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

from thalimage.core.derived_files import DerivedDirs, link_derived, remove_derived
from thalimage.core.hasher import content_hash
from thalimage.core.metadata import EXTRACTOR_VERSION, ImageMetadata, extract_metadata
from thalimage.core.perceptual_hash import PERCEPTUAL_HASH_VERSION, perceptual_hash
from thalimage.core.picture_hash import HASH_VERSION, picture_hash
from thalimage.core.scanner import Listing, SourceUnavailable, scan_directory
from thalimage.core.sidecars import digest, names_any
from thalimage.core.thumbnails import generate_thumbnail
from thalimage.core.video import (
    extract_video_info,
    extract_video_thumbnail,
    ffmpeg_available,
    is_video,
)
from thalimage.services.file_changes import SourceNotWritable
from thalimage.services.folders import is_folder_tag
from thalimage.services.identity import rekey_image
from thalimage.services.locations import EARLIEST_CREATED, sync_images
from thalimage.services.playable_copies import prepare_playable_copies

logger = logging.getLogger(__name__)


class ScanResult(BaseModel):
    scanned: int = 0
    added: int = 0
    skipped: int = 0
    errors: int = 0
    sidecars_added: int = 0
    sidecars_changed: int = 0
    sidecars_removed: int = 0
    renamed: int = 0


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
    file_hash: str  # of the whole file: its version, which metadata is kept by
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
    perceptual_hash: Optional[int]  # None for videos
    # The file is unchanged since the last scan, which keyed it with an
    # older hash: its image takes the new key rather than becoming new.
    rekey: bool = False


def run_scan(
    conn: sqlite3.Connection,
    source_id: int,
    thumb_dir: Path,
    *,
    preview_dir: Optional[Path] = None,
    video_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[..., None]] = None,
) -> ScanResult:
    """Run a full scan for a source folder.

    1. List the source folder (fails if it cannot be read)
    2. Skip unchanged files (same relative path + mtime + size)
    3. Hash, extract metadata and thumbnail new or changed files
    4. Write them to the DB in short batches
    5. Drop the locations of files that are gone; an image with no location
       left anywhere is marked deleted
    6. Record the other files: sidecars, and orphans no media file names
    7. Rename the files to their picture hash, if the source is set to
    8. With a video_dir, make playable copies of the videos iOS cannot play
    """
    source = conn.execute(
        "SELECT * FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    source_path = Path(source["path"])

    # Step 1: list files
    listing = scan_directory(source_path, recursive=bool(source["recursive"]))

    dirs = DerivedDirs(thumbs=thumb_dir, previews=preview_dir, videos=video_dir)

    # What the last scan found here, by relative path, with the extractor
    # version its metadata came from, the hash version that keyed it and the
    # version of its image's perceptual hash.
    known = {
        row["relative_path"]: row
        for row in conn.execute(
            "SELECT l.content_hash, l.relative_path, l.file_modified, l.file_size, l.hash_version,"
            " COALESCE(m.extractor_version, 0) AS extractor_version,"
            " COALESCE(i.perceptual_hash_version, 0) AS perceptual_hash_version"
            " FROM image_locations l"
            " LEFT JOIN file_metadata m ON m.file_hash = l.file_hash"
            " LEFT JOIN images i ON i.content_hash = l.content_hash"
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
    # What could not be indexed, and why: relative path -> reason.
    failures: dict[str, str] = {
        str(d.relative_to(source_path)) + os.sep: "Folder could not be read"
        for d in listing.unreadable
    }
    pending: list[_Indexed] = []
    last_write = time.monotonic()

    for processed, file_path in enumerate(listing.files, start=1):
        relative = str(file_path.relative_to(source_path))
        previous = known.get(relative)
        try:
            stat = file_path.stat()
            # Step 2: skip unchanged files whose metadata, key and perceptual
            # hash are current
            # What the last scan recorded, if the file has not changed since.
            unchanged = (
                previous if previous is not None and unchanged_since_scan(stat, previous) else None
            )
            if (
                unchanged is not None
                and unchanged["extractor_version"] >= EXTRACTOR_VERSION
                and unchanged["hash_version"] >= HASH_VERSION
                and unchanged["perceptual_hash_version"] >= PERCEPTUAL_HASH_VERSION
            ):
                kept.add(relative)
                result.skipped += 1
            else:
                # Step 3: read the file
                rekey_from = (
                    unchanged["content_hash"]
                    if unchanged is not None and unchanged["hash_version"] < HASH_VERSION
                    else None
                )
                item = _index_file(file_path, relative, stat, dirs, rekey_from)
                kept.add(relative)
                pending.append(item)
                result.added += 1
        except _SkipFile as exc:
            logger.warning("Skipping %s: %s", file_path, exc)
            result.errors += 1
            failures[relative] = str(exc)
        except Exception as exc:
            logger.exception("Failed to process %s during scan", file_path)
            result.errors += 1
            failures[relative] = _reason(exc, file_path, relative)
            kept.add(relative)

        # Step 4: write in batches
        if pending and (
            len(pending) >= BATCH_FILES or time.monotonic() - last_write >= BATCH_SECONDS
        ):
            _write_batch(conn, source_id, pending, dirs)
            pending = []
            last_write = time.monotonic()

        if progress_callback:
            progress_callback(
                current=processed,
                added=result.added,
                skipped=result.skipped,
                errors=result.errors,
            )

    _write_batch(conn, source_id, pending, dirs)

    # Step 5: drop the locations of files that are gone. Nothing under a
    # folder that could not be listed counts as gone: its contents are unknown.
    unreadable = [p for p in failures if p.endswith(os.sep)]
    gone = [
        relative
        for relative in known
        if relative not in kept and not any(relative.startswith(p) for p in unreadable)
    ]
    # Step 6: read the other files that changed, outside the transaction
    sidecars, sidecars_gone = _read_sidecars(
        conn, source_id, source_path, listing, unreadable, result, failures
    )
    with conn:
        # Their current keys: re-keying this scan may have changed them.
        gone_keys = [_location_key(conn, source_id, relative) for relative in gone]
        conn.executemany(
            "DELETE FROM image_locations WHERE source_id = ? AND relative_path = ?",
            [(source_id, relative) for relative in gone],
        )
        sync_images(conn, (k for k in gone_keys if k is not None))
        conn.executemany(
            "DELETE FROM sidecars WHERE source_id = ? AND relative_path = ?",
            [(source_id, relative) for relative in sidecars_gone],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO sidecars"
            " (source_id, relative_path, digest, file_size, file_modified, orphan)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            sidecars,
        )
        conn.execute("DELETE FROM scan_failures WHERE source_id = ?", (source_id,))
        conn.executemany(
            "INSERT INTO scan_failures (source_id, relative_path, reason) VALUES (?, ?, ?)",
            [(source_id, path, reason) for path, reason in failures.items()],
        )
        conn.execute(
            "UPDATE sources SET last_scan = datetime('now') WHERE id = ?",
            (source_id,),
        )

    # Ensure the source preset collection exists (no image sync needed — it's dynamic)
    from thalimage.services.collection_service import get_or_create_source_preset

    label = source["label"] or source_path.name
    get_or_create_source_preset(conn, source_id, label)

    # Step 7: rename the files to their picture hash, where the source asks
    if source["rename_to_hash"]:
        _rename_files(conn, source_id, result)

    # Step 8: playable copies, after the index is written: a long transcode
    # must not hold back what the scan found.
    if video_dir is not None and ffmpeg_available():
        result.errors += prepare_playable_copies(
            conn, source_id, video_dir, progress_callback=progress_callback
        )

    return result


def _rename_files(conn: sqlite3.Connection, source_id: int, result: ScanResult) -> None:
    """Rename the source's files to their picture hash, listing those that
    could not be among the scan's failures; the source folder itself when
    it refuses writes."""
    from thalimage.services.file_renaming import rename_source_files

    try:
        renaming = rename_source_files(conn, source_id)
        failed = [(path, error) for _, path, error in renaming.failed]
        result.renamed = len(renaming.renamed)
    except SourceNotWritable as exc:
        logger.warning("Not renaming the files of source %d: %s", source_id, exc)
        failed = [("." + os.sep, str(exc))]
    result.errors += len(failed)
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO scan_failures (source_id, relative_path, reason)"
            " VALUES (?, ?, ?)",
            [(source_id, path, f"Not renamed: {error}") for path, error in failed],
        )


def _read_sidecars(
    conn: sqlite3.Connection,
    source_id: int,
    source_path: Path,
    listing: Listing,
    unreadable: list[str],
    result: ScanResult,
    failures: dict[str, str],
) -> tuple[list[tuple[object, ...]], list[str]]:
    """The sidecar rows to write, and the paths of those that are gone,
    counting what was added, changed and removed. A file is read again
    only if it changed since the last scan; one that cannot be read keeps
    its row."""
    known = {
        row["relative_path"]: row
        for row in conn.execute(
            "SELECT relative_path, digest, file_size, file_modified FROM sidecars"
            " WHERE source_id = ?",
            (source_id,),
        )
    }
    media: dict[Path, list[Path]] = {}
    for file_path in listing.files:
        media.setdefault(file_path.parent, []).append(file_path)

    rows: list[tuple[object, ...]] = []
    seen: set[str] = set()
    for path in listing.others:
        relative = str(path.relative_to(source_path))
        seen.add(relative)
        previous = known.get(relative)
        try:
            stat = path.stat()
            if previous is not None and unchanged_since_scan(stat, previous):
                d = previous["digest"]
            else:
                d = digest(path)
        except OSError as exc:
            logger.warning("Cannot read sidecar %s: %s", path, exc)
            result.errors += 1
            failures[relative] = _reason(exc, path, relative)
            continue
        if previous is None:
            result.sidecars_added += 1
        elif previous["digest"] != d:
            result.sidecars_changed += 1
        orphan = not names_any(path, media.get(path.parent, []))
        rows.append(
            (source_id, relative, d, stat.st_size, _iso(stat.st_mtime), int(orphan))
        )

    gone = [
        relative
        for relative in known
        if relative not in seen and not any(relative.startswith(p) for p in unreadable)
    ]
    result.sidecars_removed = len(gone)
    return rows, gone


def _reason(exc: Exception, path: Path, relative: str) -> str:
    # The path is listed beside the reason already; keep it short.
    reason = str(exc).replace(str(path), relative)
    return f"{type(exc).__name__}: {reason}"


def _birthtime(stat: os.stat_result) -> Optional[float]:
    """The file's creation time where the platform reports one (macOS,
    BSD); Linux does not, and gives None."""
    return getattr(stat, "st_birthtime", None)


def unchanged_since_scan(stat: os.stat_result, location: sqlite3.Row) -> bool:
    """Whether a file still has the modification time and size its
    location row recorded: the scan's test for "not changed"."""
    return bool(
        location["file_modified"] == _iso(stat.st_mtime) and location["file_size"] == stat.st_size
    )


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _index_file(
    file_path: Path,
    relative: str,
    stat: os.stat_result,
    dirs: DerivedDirs,
    rekey_from: Optional[str] = None,
) -> _Indexed:
    """Hash a file, read its dimensions and metadata, write its thumbnail.
    With `rekey_from`, the key its image had until now: its derived files
    are linked to the new key first, so none is made again."""
    birthtime = _birthtime(stat)
    h = picture_hash(file_path)
    file_hash = content_hash(file_path)
    if rekey_from is not None:
        link_derived(dirs, rekey_from, h)

    meta: Optional[ImageMetadata]
    if is_video(file_path):
        if not ffmpeg_available():
            raise _SkipFile("ffmpeg not available")
        info = extract_video_info(file_path)
        extract_video_thumbnail(file_path, dirs.thumbs, h)
        width, height = int(info["width"]), int(info["height"])
        aspect = width / height if height else 1.0
        fmt = file_path.suffix.lstrip(".").upper()
        meta = None
        perceptual: Optional[int] = None
    else:
        meta = extract_metadata(file_path)
        generate_thumbnail(file_path, dirs.thumbs, h)
        width, height = meta.file_info.width, meta.file_info.height
        aspect = meta.file_info.aspect_ratio
        fmt = meta.file_info.format
        perceptual = perceptual_hash(file_path)

    return _Indexed(
        content_hash=h,
        file_hash=file_hash,
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
        perceptual_hash=perceptual,
        rekey=rekey_from is not None,
    )


def _write_batch(
    conn: sqlite3.Connection,
    source_id: int,
    items: list[_Indexed],
    dirs: DerivedDirs,
) -> None:
    """Write indexed files in one short transaction, then drop the derived
    files of the keys it retired."""
    if not items:
        return
    retired: set[str] = set()
    with conn:
        touched: set[str] = set()
        for item in items:
            previous = _location_key(conn, source_id, item.relative_path)
            if item.rekey and previous is not None and previous != item.content_hash:
                rekey_image(conn, previous, item.content_hash)
                retired.add(previous)
            _upsert_image(conn, source_id, item)
            if item.meta is not None:
                _tag_from_file(conn, item.content_hash, item.meta)
            _upsert_metadata(conn, item)
            _upsert_location(conn, source_id, item)
            touched.add(item.content_hash)
            if previous is not None:
                # The path may have held other content until now.
                touched.add(previous)
        sync_images(conn, touched - retired)
    for key in retired:
        remove_derived(dirs, key)


def _location_key(conn: sqlite3.Connection, source_id: int, relative: str) -> Optional[str]:
    """The key of the image at a location, if the location is known."""
    row = conn.execute(
        "SELECT content_hash FROM image_locations WHERE source_id = ? AND relative_path = ?",
        (source_id, relative),
    ).fetchone()
    return row["content_hash"] if row else None


def _upsert_image(conn: sqlite3.Connection, source_id: int, item: _Indexed) -> None:
    """Insert new content with this file as its primary location. Content
    already known keeps its primary location; sync_images moves it only if
    that location is gone."""
    conn.execute(
        """INSERT INTO images
           (content_hash, filename, source_id, relative_path,
            file_size, width, height, aspect_ratio, format,
            file_modified, file_created, thumb_generated,
            perceptual_hash, perceptual_hash_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
           ON CONFLICT(content_hash) DO UPDATE SET
            width=excluded.width,
            height=excluded.height,
            aspect_ratio=excluded.aspect_ratio,
            format=excluded.format,
            thumb_generated=1,
            perceptual_hash=excluded.perceptual_hash,
            perceptual_hash_version=excluded.perceptual_hash_version
        """,
        (item.content_hash, item.filename, source_id, item.relative_path,
         item.file_size, item.width, item.height, item.aspect_ratio, item.format,
         item.file_modified, item.file_created, item.perceptual_hash, PERCEPTUAL_HASH_VERSION),
    )


def _upsert_location(conn: sqlite3.Connection, source_id: int, item: _Indexed) -> None:
    conn.execute(
        """INSERT INTO image_locations
           (source_id, relative_path, content_hash, filename,
            file_size, file_modified, file_created, hash_version, file_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_id, relative_path) DO UPDATE SET
            content_hash=excluded.content_hash,
            hash_version=excluded.hash_version,
            file_hash=excluded.file_hash,
            filename=excluded.filename,
            file_size=excluded.file_size,
            file_modified=excluded.file_modified,
            file_created=""" + EARLIEST_CREATED.format(new="excluded.file_created", old="file_created"),
        (source_id, item.relative_path, item.content_hash, item.filename,
         item.file_size, item.file_modified, item.file_created, HASH_VERSION, item.file_hash),
    )


def _file_tag_names(meta: ImageMetadata) -> list[str]:
    stars = [f"rating:{meta.rating}"] if meta.rating else []
    # Folder tags come from where the file is, never from what it says.
    return [k for k in meta.keywords if not is_folder_tag(k)] + stars


def _tag_from_file(conn: sqlite3.Connection, h: str, meta: ImageMetadata) -> None:
    """Tag an image with the keywords and rating in its file. Only names
    not imported from any of its files before are added: a tag the user
    removed stays removed. A name matches an existing tag whatever its
    case."""
    row = conn.execute("SELECT file_tags FROM images WHERE content_hash = ?", (h,)).fetchone()
    imported = set(json.loads(row["file_tags"])) if row and row["file_tags"] else set()
    names = _file_tag_names(meta)
    conn.execute(
        "UPDATE images SET file_tags = ? WHERE content_hash = ?",
        (json.dumps(sorted(imported | set(names))), h),
    )
    for name in names:
        if name in imported:
            continue
        tag = conn.execute("SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        tag_id = tag["id"] if tag else conn.execute(
            "INSERT INTO tags (name) VALUES (?)", (name,)
        ).lastrowid
        conn.execute(
            "INSERT OR IGNORE INTO image_tags (image_hash, tag_id) VALUES (?, ?)", (h, tag_id)
        )


# A file version keeps the first name it was scanned under.
_KEEP_ORIGINAL_NAME = "original_name = COALESCE(original_name, excluded.original_name)"


def _upsert_metadata(conn: sqlite3.Connection, item: _Indexed) -> None:
    """Record what was read from the file version, for the image it shows."""
    meta = item.meta
    if meta is None:
        # Videos carry no AI metadata; keep an empty row so joins line up.
        conn.execute(
            "INSERT INTO file_metadata (file_hash, content_hash, extractor_version, original_name)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(file_hash) DO UPDATE SET content_hash = excluded.content_hash,"
            " extractor_version = excluded.extractor_version, " + _KEEP_ORIGINAL_NAME,
            (item.file_hash, item.content_hash, EXTRACTOR_VERSION, item.filename),
        )
        return
    ai = meta.ai_params
    conn.execute(
        """INSERT INTO file_metadata
           (file_hash, content_hash, ai_tool, prompt, negative_prompt,
            raw_params, exif_data, png_text, extractor_version, original_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(file_hash) DO UPDATE SET
            content_hash=excluded.content_hash,
            extractor_version=excluded.extractor_version,
            ai_tool=excluded.ai_tool,
            prompt=excluded.prompt,
            negative_prompt=excluded.negative_prompt,
            raw_params=excluded.raw_params,
            exif_data=excluded.exif_data,
            png_text=excluded.png_text,
            extracted_at=datetime('now'),
        """ + _KEEP_ORIGINAL_NAME,
        (
            item.file_hash,
            item.content_hash,
            ai.tool if ai else None,
            ai.prompt if ai else None,
            ai.negative_prompt if ai else None,
            ai.raw_params if ai else None,
            json.dumps(meta.exif_data) if meta.exif_data else None,
            json.dumps(meta.png_text) if meta.png_text else None,
            EXTRACTOR_VERSION,
            item.filename,
        ),
    )
