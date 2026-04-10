"""Scan orchestration: discover → hash → metadata → thumbnail → DB."""

import json
import logging
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from thalimage.core.hasher import content_hash
from thalimage.core.metadata import extract_metadata
from thalimage.core.scanner import scan_directory
from thalimage.core.thumbnails import generate_thumbnail
from thalimage.core.video import (
    extract_video_info,
    extract_video_thumbnail,
    ffmpeg_available,
    is_video,
)

logger = logging.getLogger(__name__)


class ScanResult(BaseModel):
    scanned: int = 0
    added: int = 0
    skipped: int = 0
    errors: int = 0


def run_scan(
    conn: sqlite3.Connection,
    source_id: int,
    thumb_dir: Path,
    *,
    progress_callback: Optional[Callable[..., None]] = None,
) -> ScanResult:
    """Run a full scan for a source folder.

    1. Walk source directory
    2. Skip unchanged files (same path + mtime + size)
    3. Hash, extract metadata, generate thumbnails for new/changed files
    4. Upsert into DB
    5. Mark deleted files
    """
    source = conn.execute(
        "SELECT * FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    source_path = Path(source["path"])
    recursive = bool(source["recursive"])

    # Step 1: discover files
    paths = scan_directory(source_path, recursive=recursive)

    result = ScanResult(scanned=len(paths))

    if progress_callback:
        progress_callback(phase="processing", total=len(paths), current=0)

    # Build lookup of existing images for this source
    existing = {}
    for row in conn.execute(
        "SELECT content_hash, relative_path, file_modified, file_size "
        "FROM images WHERE source_id = ? AND deleted = 0",
        (source_id,),
    ).fetchall():
        existing[row["relative_path"]] = row

    seen_hashes: set[str] = set()
    processed = 0

    for file_path in paths:
        try:
            relative = str(file_path.relative_to(source_path))
            stat = file_path.stat()
            mtime_iso = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat()
            ctime_iso = None
            birthtime = getattr(stat, "st_birthtime", None)
            if birthtime:
                ctime_iso = datetime.fromtimestamp(
                    birthtime, tz=timezone.utc
                ).isoformat()

            # Check if file is unchanged
            if relative in existing:
                row = existing[relative]
                if row["file_modified"] == mtime_iso and row["file_size"] == stat.st_size:
                    seen_hashes.add(row["content_hash"])
                    result.skipped += 1
                    continue

            # Step 3: hash
            h = content_hash(file_path)
            seen_hashes.add(h)

            if is_video(file_path):
                if not ffmpeg_available():
                    logger.warning("Skipping video %s: ffmpeg not available", file_path)
                    result.errors += 1
                    continue

                # Video: extract info via ffprobe, thumbnail via ffmpeg
                info = extract_video_info(file_path)
                extract_video_thumbnail(file_path, thumb_dir, h)
                width = info["width"]
                height = info["height"]
                aspect = width / height if height else 1.0
                fmt = file_path.suffix.lstrip(".").upper()

                conn.execute(
                    """INSERT INTO images
                       (content_hash, filename, source_id, relative_path,
                        file_size, width, height, aspect_ratio, format,
                        file_modified, file_created, thumb_generated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                       ON CONFLICT(content_hash) DO UPDATE SET
                        filename=excluded.filename,
                        relative_path=excluded.relative_path,
                        file_size=excluded.file_size,
                        file_modified=excluded.file_modified,
                        thumb_generated=1,
                        deleted=0
                    """,
                    (h, file_path.name, source_id, relative,
                     stat.st_size, width, height, aspect, fmt,
                     mtime_iso, ctime_iso),
                )

                # No AI metadata for videos
                conn.execute(
                    """INSERT INTO image_metadata (content_hash)
                       VALUES (?)
                       ON CONFLICT(content_hash) DO NOTHING
                    """,
                    (h,),
                )
            else:
                # Image: extract metadata via PIL, thumbnail via PIL
                meta = extract_metadata(file_path)
                generate_thumbnail(file_path, thumb_dir, h)

                conn.execute(
                    """INSERT INTO images
                       (content_hash, filename, source_id, relative_path,
                        file_size, width, height, aspect_ratio, format,
                        file_modified, file_created, thumb_generated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                       ON CONFLICT(content_hash) DO UPDATE SET
                        filename=excluded.filename,
                        relative_path=excluded.relative_path,
                        file_size=excluded.file_size,
                        file_modified=excluded.file_modified,
                        thumb_generated=1,
                        deleted=0
                    """,
                    (
                        h,
                        file_path.name,
                        source_id,
                        relative,
                        stat.st_size,
                        meta.file_info.width,
                        meta.file_info.height,
                        meta.file_info.aspect_ratio,
                        meta.file_info.format,
                        mtime_iso,
                        ctime_iso,
                    ),
                )

                ai = meta.ai_params
                conn.execute(
                    """INSERT INTO image_metadata
                       (content_hash, ai_tool, prompt, negative_prompt,
                        raw_params, exif_data, png_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(content_hash) DO UPDATE SET
                        ai_tool=excluded.ai_tool,
                        prompt=excluded.prompt,
                        negative_prompt=excluded.negative_prompt,
                        raw_params=excluded.raw_params,
                        exif_data=excluded.exif_data,
                        png_text=excluded.png_text,
                        extracted_at=datetime('now')
                    """,
                    (
                        h,
                        ai.tool if ai else None,
                        ai.prompt if ai else None,
                        ai.negative_prompt if ai else None,
                        ai.raw_params if ai else None,
                        json.dumps(meta.exif_data) if meta.exif_data else None,
                        json.dumps(meta.png_text) if meta.png_text else None,
                    ),
                )

            result.added += 1

        except Exception:
            result.errors += 1

        processed += 1
        if progress_callback:
            progress_callback(
                current=processed,
                added=result.added,
                skipped=result.skipped,
                errors=result.errors,
            )

    conn.commit()

    # Step 7: mark deleted files
    all_hashes = {
        row[0]
        for row in conn.execute(
            "SELECT content_hash FROM images WHERE source_id = ? AND deleted = 0",
            (source_id,),
        ).fetchall()
    }
    deleted_hashes = all_hashes - seen_hashes
    if deleted_hashes:
        placeholders = ",".join("?" * len(deleted_hashes))
        conn.execute(
            f"UPDATE images SET deleted = 1 WHERE content_hash IN ({placeholders})",
            list(deleted_hashes),
        )
        conn.commit()

    # Update last_scan timestamp
    conn.execute(
        "UPDATE sources SET last_scan = datetime('now') WHERE id = ?",
        (source_id,),
    )
    conn.commit()

    # Sync source preset collection
    from thalimage.services.collection_service import (
        get_or_create_source_preset,
        sync_source_preset_images,
    )

    label = source["label"] or Path(source["path"]).name
    preset = get_or_create_source_preset(conn, source_id, label)
    sync_source_preset_images(conn, preset.id, source_id)

    return result
