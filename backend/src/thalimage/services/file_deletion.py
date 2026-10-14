"""Deleting copies of an image from disk."""

import os
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

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
    failed: list[tuple[str, str]] = field(default_factory=list)  # (path, error)


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
    paths = list(dict.fromkeys(paths))

    locations = {}
    for path in paths:
        row = conn.execute(
            "SELECT content_hash, file_modified, file_size FROM image_locations"
            " WHERE source_id = ? AND relative_path = ?",
            (source_id, path),
        ).fetchone()
        if row is None:
            raise UnknownCopy(f"{path} is not an indexed file of this source.")
        locations[path] = row

    for content_hash, deleting in Counter(r["content_hash"] for r in locations.values()).items():
        copies = conn.execute(
            "SELECT COUNT(*) FROM image_locations WHERE content_hash = ?", (content_hash,)
        ).fetchone()[0]
        if copies - deleting < 1:
            named = ", ".join(p for p, r in locations.items() if r["content_hash"] == content_hash)
            raise DeletionRefused(
                f"{named} is the only copy of its image."
                if copies == 1
                else f"{named} are every copy of one image; keep at least one."
            )

    for path, location in locations.items():
        try:
            unchanged = unchanged_since_scan((root / path).stat(), location)
        except FileNotFoundError:
            unchanged = False
        if not unchanged:
            raise DeletionRefused(f"{path} changed since the last scan; rescan first.")

    result = DeletionResult()
    for path, location in locations.items():
        try:
            os.remove(root / path)
        except OSError as exc:
            record_change(conn, source_id, "delete", path, outcome="failed", error=str(exc))
            result.failed.append((path, str(exc)))
            continue
        record_change(conn, source_id, "delete", path, outcome="done")
        with conn:
            conn.execute(
                "DELETE FROM image_locations WHERE source_id = ? AND relative_path = ?",
                (source_id, path),
            )
            sync_images(conn, [location["content_hash"]])
        result.deleted.append(path)
    return result
