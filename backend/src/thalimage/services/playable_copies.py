"""Playable copies of the videos iOS cannot play, made at scan time."""

import logging
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Optional

from thalimage.core.video import (
    VIDEO_EXTENSIONS,
    make_playable_copy,
    playable_copy_args,
    playable_copy_path,
    probe_streams,
)

logger = logging.getLogger(__name__)

# A video's format is its extension, upper-cased (scan_service._index_file).
_VIDEO_FORMATS = ", ".join(f"'{ext.lstrip('.').upper()}'" for ext in sorted(VIDEO_EXTENSIONS))


def prepare_playable_copies(
    conn: sqlite3.Connection,
    source_id: int,
    video_dir: Path,
    *,
    progress_callback: Optional[Callable[..., None]] = None,
) -> int:
    """Probe the source's videos not probed yet, then make the missing
    copies of those iOS cannot play. Returns how many could not be probed
    or copied; each failure is logged and leaves the video as it is."""
    root = Path(conn.execute("SELECT path FROM sources WHERE id = ?", (source_id,)).fetchone()[0])
    videos = conn.execute(
        f"""SELECT i.content_hash, i.needs_playable_copy, MIN(l.relative_path) AS relative_path
            FROM images i JOIN image_locations l ON l.content_hash = i.content_hash
            WHERE l.source_id = ? AND i.deleted = 0 AND i.format IN ({_VIDEO_FORMATS})
            GROUP BY i.content_hash""",
        (source_id,),
    ).fetchall()

    errors = 0
    to_copy: list[tuple[str, Path, list[str]]] = []
    for v in videos:
        if v["needs_playable_copy"] == 0:
            continue
        path = root / v["relative_path"]
        if v["needs_playable_copy"] is not None and playable_copy_path(
            video_dir, v["content_hash"]
        ).exists():
            continue
        try:
            args = playable_copy_args(path.suffix, probe_streams(path))
        except Exception:
            logger.exception("Could not probe %s", path)
            errors += 1
            continue
        with conn:
            conn.execute(
                "UPDATE images SET needs_playable_copy = ? WHERE content_hash = ?",
                (args is not None, v["content_hash"]),
            )
        if args is not None and not playable_copy_path(video_dir, v["content_hash"]).exists():
            to_copy.append((v["content_hash"], path, args))

    if progress_callback and to_copy:
        progress_callback(phase="converting", total=len(to_copy), current=0)
    for done, (content_hash, path, args) in enumerate(to_copy, start=1):
        try:
            make_playable_copy(path, playable_copy_path(video_dir, content_hash), args)
        except Exception:
            logger.exception("Could not make a playable copy of %s", path)
            errors += 1
        if progress_callback:
            progress_callback(current=done)
    return errors


def remove_playable_copies(video_dir: Path, hashes: Iterable[str]) -> None:
    for h in hashes:
        playable_copy_path(video_dir, h).unlink(missing_ok=True)
