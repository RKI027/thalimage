"""Deleting image files from disk: copies of an image, or a whole image."""

import os
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from thalimage.services.file_changes import record_change, writable_root
from thalimage.services.locations import sync_images
from thalimage.services.scan_service import unchanged_since_scan


class UnknownCopy(ValueError):
    """The path is not an indexed file of the source."""


class DeletionRefused(Exception):
    """Deleting would lose an image, or act on a file the index no longer
    describes."""


@dataclass
class DeletionResult:
    deleted: list[str] = field(default_factory=list)
    failed: list[tuple[int, str, str]] = field(default_factory=list)  # (source, path, error)


class Copy(BaseModel):
    """One file holding an image's content."""

    source_id: int
    source_path: str
    relative_path: str
    writable: bool


@dataclass
class _Target:
    source_id: int
    root: Path
    path: str
    location: sqlite3.Row


_LOCATION = (
    "SELECT content_hash, file_modified, file_size FROM image_locations"
    " WHERE source_id = ? AND relative_path = ?"
)


def delete_copies(conn: sqlite3.Connection, source_id: int, paths: list[str]) -> DeletionResult:
    """Delete these files (relative to the source) from disk, each a copy
    of an image that keeps at least one other copy.

    Everything is checked before anything is deleted: the source must be
    writable (LookupError, SourceNotWritable), each path an indexed file
    of it (UnknownCopy), and no image may lose its last copy, nor a file
    have changed since it was scanned (DeletionRefused). A removal that
    then fails is reported in the result; every attempt is recorded.
    """
    root = writable_root(conn, source_id)
    targets = []
    for path in dict.fromkeys(paths):
        row = conn.execute(_LOCATION, (source_id, path)).fetchone()
        if row is None:
            raise UnknownCopy(f"{path} is not an indexed file of this source.")
        targets.append(_Target(source_id, root, path, row))

    for content_hash, deleting in Counter(t.location["content_hash"] for t in targets).items():
        copies = conn.execute(
            "SELECT COUNT(*) FROM image_locations WHERE content_hash = ?", (content_hash,)
        ).fetchone()[0]
        if copies - deleting < 1:
            named = ", ".join(t.path for t in targets if t.location["content_hash"] == content_hash)
            raise DeletionRefused(
                f"{named} is the only copy of its image."
                if copies == 1
                else f"{named} are every copy of one image; keep at least one."
            )

    return _remove(conn, targets)


def image_copies(conn: sqlite3.Connection, content_hash: str) -> list[Copy] | None:
    """Every file holding a live image, by source then path; None if there
    is no such image."""
    if conn.execute(
        "SELECT 1 FROM images WHERE content_hash = ? AND deleted = 0", (content_hash,)
    ).fetchone() is None:
        return None
    rows = conn.execute(
        """SELECT l.source_id, s.path AS source_path, l.relative_path, s.writable
           FROM image_locations l JOIN sources s ON s.id = l.source_id
           WHERE l.content_hash = ?
           ORDER BY l.source_id, l.relative_path""",
        (content_hash,),
    ).fetchall()
    return [Copy(**dict(r)) for r in rows]


def delete_image(conn: sqlite3.Connection, content_hash: str) -> DeletionResult | None:
    """Delete every copy of an image, in every source, from disk; None if
    there is no such image.

    Refused as a whole unless every source holding a copy is writable
    (SourceNotWritable) and no copy changed since it was scanned
    (DeletionRefused). Once its last copy is gone the image is marked
    deleted, keeping its tags, scores, votes and collections.
    """
    copies = image_copies(conn, content_hash)
    if copies is None:
        return None
    roots = {c.source_id: writable_root(conn, c.source_id) for c in copies}
    targets = [
        _Target(
            c.source_id,
            roots[c.source_id],
            c.relative_path,
            conn.execute(_LOCATION, (c.source_id, c.relative_path)).fetchone(),
        )
        for c in copies
    ]
    return _remove(conn, targets)


def _remove(conn: sqlite3.Connection, targets: list[_Target]) -> DeletionResult:
    """Refuse if any file changed since it was scanned, then remove each,
    recording every attempt and dropping its location."""
    for t in targets:
        try:
            unchanged = unchanged_since_scan((t.root / t.path).stat(), t.location)
        except FileNotFoundError:
            unchanged = False
        if not unchanged:
            raise DeletionRefused(f"{t.path} changed since the last scan; rescan first.")

    result = DeletionResult()
    for t in targets:
        try:
            os.remove(t.root / t.path)
        except OSError as exc:
            record_change(conn, t.source_id, "delete", t.path, outcome="failed", error=str(exc))
            result.failed.append((t.source_id, t.path, str(exc)))
            continue
        record_change(conn, t.source_id, "delete", t.path, outcome="done")
        with conn:
            conn.execute(
                "DELETE FROM image_locations WHERE source_id = ? AND relative_path = ?",
                (t.source_id, t.path),
            )
            sync_images(conn, [t.location["content_hash"]])
        result.deleted.append(t.path)
    return result
