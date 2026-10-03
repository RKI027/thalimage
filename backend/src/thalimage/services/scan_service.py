"""Scan orchestration: discover → hash → metadata → thumbnail → DB."""

import json
import logging
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from thalimage.core.hasher import content_hash
from thalimage.core.metadata import EXTRACTOR_VERSION, ImageMetadata, extract_metadata
from thalimage.core.scanner import SourceUnavailable, scan_directory
from thalimage.core.thumbnails import generate_thumbnail
from thalimage.core.video import (
    extract_video_info,
    extract_video_thumbnail,
    ffmpeg_available,
    is_video,
)
from thalimage.services.locations import sync_images

logger = logging.getLogger(__name__)


class ScanResult(BaseModel):
    scanned: int = 0
    added: int = 0
    skipped: int = 0
    errors: int = 0


# Indexed files are written in batches of at most this many files, or
# whatever accumulated in this many seconds. The slow work (hashing,
# probing, thumbnailing) happens outside any transaction, so other
# connections only ever wait for one batch's inserts.
BATCH_FILES = 50
BATCH_SECONDS = 1.0


class _SkipFile(Exception):
    """The file is supported in principle but cannot be indexed here."""


@dataclass
class _Indexed:
    """One file, read and thumbnailed, ready to be written."""

    content_hash: str
    filename: str
    relative_path: str
    file_size: int
    file_modified: str
    file_created: Optional[str]
    width: int
    height: int
    aspect_ratio: float
    format: str
    meta: Optional[ImageMetadata]  # None for videos: no AI metadata


def run_scan(
    conn: sqlite3.Connection,
    source_id: int,
    thumb_dir: Path,
    *,
    progress_callback: Optional[Callable[..., None]] = None,
) -> ScanResult:
    """Run a full scan for a source folder.

    1. List the source folder (fails if it cannot be read)
    2. Skip unchanged files (same relative path + mtime + size)
    3. Hash, extract metadata and thumbnail new or changed files
    4. Write them to the DB in short batches
    5. Drop the locations of files that are gone; an image with no location
       left anywhere is marked deleted
    """
    source = conn.execute(
        "SELECT * FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    source_path = Path(source["path"])

    # Step 1: list files
    listing = scan_directory(source_path, recursive=bool(source["recursive"]))

    # What the last scan found here, by relative path, with the extractor
    # version its metadata came from.
    known = {
        row["relative_path"]: row
        for row in conn.execute(
            "SELECT l.content_hash, l.relative_path, l.file_modified, l.file_size,"
            " COALESCE(m.extractor_version, 0) AS extractor_version"
            " FROM image_locations l"
            " LEFT JOIN image_metadata m ON m.content_hash = l.content_hash"
            " WHERE l.source_id = ?",
            (source_id,),
        )
    }
    if not listing.files and known:
        raise SourceUnavailable(
            f"{source_path} has no files, but {len(known)} were indexed from it."
            " Not marking them deleted: is the folder mounted?"
        )

    result = ScanResult(scanned=len(listing.files))
    if progress_callback:
        progress_callback(phase="processing", total=len(listing.files), current=0)

    # Paths whose location row stays. A file that cannot be read keeps its
    # previous row rather than reading as deleted.
    kept: set[str] = set()
    pending: list[_Indexed] = []
    last_write = time.monotonic()

    for processed, file_path in enumerate(listing.files, start=1):
        relative = str(file_path.relative_to(source_path))
        previous = known.get(relative)
        try:
            stat = file_path.stat()
            modified = _iso(stat.st_mtime)
            # Step 2: skip unchanged files whose metadata is current
            if (
                previous is not None
                and previous["file_modified"] == modified
                and previous["file_size"] == stat.st_size
                and previous["extractor_version"] >= EXTRACTOR_VERSION
            ):
                kept.add(relative)
                result.skipped += 1
            else:
                # Step 3: read the file
                item = _index_file(file_path, relative, stat, thumb_dir)
                kept.add(relative)
                pending.append(item)
                result.added += 1
        except _SkipFile as exc:
            logger.warning("Skipping %s: %s", file_path, exc)
            result.errors += 1
        except Exception:
            logger.exception("Failed to process %s during scan", file_path)
            result.errors += 1
            kept.add(relative)

        # Step 4: write in batches
        if pending and (
            len(pending) >= BATCH_FILES or time.monotonic() - last_write >= BATCH_SECONDS
        ):
            _write_batch(conn, source_id, pending, known)
            pending = []
            last_write = time.monotonic()

        if progress_callback:
            progress_callback(
                current=processed,
                added=result.added,
                skipped=result.skipped,
                errors=result.errors,
            )

    _write_batch(conn, source_id, pending, known)

    # Step 5: drop the locations of files that are gone. Nothing under a
    # folder that could not be listed counts as gone: its contents are unknown.
    unreadable = [str(d.relative_to(source_path)) + os.sep for d in listing.unreadable]
    gone = [
        relative
        for relative in known
        if relative not in kept and not any(relative.startswith(p) for p in unreadable)
    ]
    with conn:
        conn.executemany(
            "DELETE FROM image_locations WHERE source_id = ? AND relative_path = ?",
            [(source_id, relative) for relative in gone],
        )
        sync_images(conn, (known[relative]["content_hash"] for relative in gone))
        conn.execute(
            "UPDATE sources SET last_scan = datetime('now') WHERE id = ?",
            (source_id,),
        )

    # Ensure the source preset collection exists (no image sync needed — it's dynamic)
    from thalimage.services.collection_service import get_or_create_source_preset

    label = source["label"] or source_path.name
    get_or_create_source_preset(conn, source_id, label)

    return result


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _index_file(
    file_path: Path, relative: str, stat: os.stat_result, thumb_dir: Path
) -> _Indexed:
    """Hash a file, read its dimensions and metadata, write its thumbnail."""
    birthtime = getattr(stat, "st_birthtime", None)
    h = content_hash(file_path)

    meta: Optional[ImageMetadata]
    if is_video(file_path):
        if not ffmpeg_available():
            raise _SkipFile("ffmpeg not available")
        info = extract_video_info(file_path)
        extract_video_thumbnail(file_path, thumb_dir, h)
        width, height = int(info["width"]), int(info["height"])
        aspect = width / height if height else 1.0
        fmt = file_path.suffix.lstrip(".").upper()
        meta = None
    else:
        meta = extract_metadata(file_path)
        generate_thumbnail(file_path, thumb_dir, h)
        width, height = meta.file_info.width, meta.file_info.height
        aspect = meta.file_info.aspect_ratio
        fmt = meta.file_info.format

    return _Indexed(
        content_hash=h,
        filename=file_path.name,
        relative_path=relative,
        file_size=stat.st_size,
        file_modified=_iso(stat.st_mtime),
        file_created=_iso(birthtime) if birthtime else None,
        width=width,
        height=height,
        aspect_ratio=aspect,
        format=fmt,
        meta=meta,
    )


def _write_batch(
    conn: sqlite3.Connection,
    source_id: int,
    items: list[_Indexed],
    known: dict[str, sqlite3.Row],
) -> None:
    """Write indexed files in one short transaction."""
    if not items:
        return
    with conn:
        touched: set[str] = set()
        for item in items:
            _upsert_image(conn, source_id, item)
            _upsert_metadata(conn, item.content_hash, item.meta)
            _upsert_location(conn, source_id, item)
            touched.add(item.content_hash)
            previous = known.get(item.relative_path)
            if previous is not None:
                # The path may have held other content until now.
                touched.add(previous["content_hash"])
        sync_images(conn, touched)


def _upsert_image(conn: sqlite3.Connection, source_id: int, item: _Indexed) -> None:
    """Insert new content with this file as its primary location. Content
    already known keeps its primary location; sync_images moves it only if
    that location is gone."""
    conn.execute(
        """INSERT INTO images
           (content_hash, filename, source_id, relative_path,
            file_size, width, height, aspect_ratio, format,
            file_modified, file_created, thumb_generated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
           ON CONFLICT(content_hash) DO UPDATE SET
            width=excluded.width,
            height=excluded.height,
            aspect_ratio=excluded.aspect_ratio,
            format=excluded.format,
            thumb_generated=1
        """,
        (item.content_hash, item.filename, source_id, item.relative_path,
         item.file_size, item.width, item.height, item.aspect_ratio, item.format,
         item.file_modified, item.file_created),
    )


def _upsert_location(conn: sqlite3.Connection, source_id: int, item: _Indexed) -> None:
    conn.execute(
        """INSERT INTO image_locations
           (source_id, relative_path, content_hash, filename,
            file_size, file_modified, file_created)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_id, relative_path) DO UPDATE SET
            content_hash=excluded.content_hash,
            filename=excluded.filename,
            file_size=excluded.file_size,
            file_modified=excluded.file_modified,
            file_created=excluded.file_created
        """,
        (source_id, item.relative_path, item.content_hash, item.filename,
         item.file_size, item.file_modified, item.file_created),
    )


def _upsert_metadata(
    conn: sqlite3.Connection, h: str, meta: Optional[ImageMetadata]
) -> None:
    if meta is None:
        # Videos carry no AI metadata; keep an empty row so joins line up.
        conn.execute(
            "INSERT INTO image_metadata (content_hash, extractor_version) VALUES (?, ?)"
            " ON CONFLICT(content_hash) DO UPDATE SET extractor_version = excluded.extractor_version",
            (h, EXTRACTOR_VERSION),
        )
        return
    ai = meta.ai_params
    conn.execute(
        """INSERT INTO image_metadata
           (content_hash, ai_tool, prompt, negative_prompt,
            raw_params, exif_data, png_text, extractor_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(content_hash) DO UPDATE SET
            extractor_version=excluded.extractor_version,
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
            EXTRACTOR_VERSION,
        ),
    )
