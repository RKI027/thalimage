"""The gate every change to a source's files goes through, and its record.

Thalimage changes files only in a source marked writable, and only once
its folder has accepted a test write: a folder mounted read-only must
refuse up front, not halfway through an operation. The module also holds
the test that a file still matches the location row its scan wrote.
"""

import os
import sqlite3
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional


class SourceNotWritable(Exception):
    """Thalimage may not, or cannot, change files in this source."""


def check_folder_accepts_writes(folder: Path) -> None:
    """Write and remove a temporary file in `folder`; SourceNotWritable if
    that fails."""
    try:
        fd, probe = tempfile.mkstemp(prefix=".thalimage-write-check-", dir=folder)
    except OSError as exc:
        raise SourceNotWritable(
            f"{folder} does not accept writes ({exc.strerror})."
            " Is it mounted read-only?"
        ) from exc
    os.close(fd)
    os.unlink(probe)


def writable_root(conn: sqlite3.Connection, source_id: int) -> Path:
    """The folder of a source Thalimage may change files in. LookupError
    for an unknown source, SourceNotWritable for one not marked writable
    or whose folder refuses writes."""
    row = conn.execute("SELECT path, writable FROM sources WHERE id = ?", (source_id,)).fetchone()
    if row is None:
        raise LookupError(f"Source {source_id} not found")
    if not row["writable"]:
        raise SourceNotWritable(f"{row['path']} is not marked writable.")
    root = Path(row["path"])
    check_folder_accepts_writes(root)
    return root


_LOCATION = (
    "SELECT content_hash, file_modified, file_size FROM image_locations"
    " WHERE source_id = ? AND relative_path = ?"
)


def location_row(conn: sqlite3.Connection, source_id: int, path: str) -> Optional[sqlite3.Row]:
    """The image location of a source-relative path, or None if it is not
    indexed."""
    row: Optional[sqlite3.Row] = conn.execute(_LOCATION, (source_id, path)).fetchone()
    return row


def iso_timestamp(timestamp: float) -> str:
    """The timestamp in the form the rows store."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def unchanged_since_scan(stat: os.stat_result, location: sqlite3.Row) -> bool:
    """Whether a file still has the modification time and size its
    location row recorded: the scan's test for "not changed"."""
    return bool(
        location["file_modified"] == iso_timestamp(stat.st_mtime)
        and location["file_size"] == stat.st_size
    )


def still_as_scanned(
    conn: sqlite3.Connection,
    source_id: int,
    root: Path,
    path: str,
    location: Optional[sqlite3.Row] = None,
) -> bool:
    """Whether the file at `path` still has the modification time and size
    its location row recorded; False when the file is gone. `location`
    saves the query when the caller already has the row."""
    if location is None:
        location = location_row(conn, source_id, path)
        if location is None:
            return False
    try:
        return unchanged_since_scan((root / path).stat(), location)
    except FileNotFoundError:
        return False


def record_change(
    conn: sqlite3.Connection,
    source_id: int,
    operation: str,
    path: str,
    *,
    outcome: Literal["done", "failed"],
    target: Optional[str] = None,
    target_source_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Record one change made (or attempted) on disk, and commit (along
    with anything the caller has pending): the record must survive
    whatever happens next. `target_source_id` is set when the change was a
    move to another source."""
    with conn:
        conn.execute(
            "INSERT INTO file_changes"
            " (source_id, operation, path, target, target_source_id, outcome, error)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source_id, operation, path, target, target_source_id, outcome, error),
        )


def change_file(
    conn: sqlite3.Connection,
    source_id: int,
    operation: str,
    path: str,
    change: Callable[[], object],
    *,
    target: Optional[str] = None,
    target_source_id: Optional[int] = None,
) -> Optional[str]:
    """Make one change on disk and record it, done or failed; the error if
    it failed."""
    try:
        change()
    except OSError as exc:
        record_change(
            conn, source_id, operation, path,
            target=target, target_source_id=target_source_id,
            outcome="failed", error=str(exc),
        )
        return str(exc)
    record_change(
        conn, source_id, operation, path,
        target=target, target_source_id=target_source_id, outcome="done",
    )
    return None
