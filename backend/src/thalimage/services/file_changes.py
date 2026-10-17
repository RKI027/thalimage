"""The gate every change to a source's files goes through, and its record.

Thalimage changes files only in a source marked writable, and only once
its folder has accepted a test write: a folder mounted read-only must
refuse up front, not halfway through an operation.
"""

import os
import sqlite3
import tempfile
from collections.abc import Callable
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


def record_change(
    conn: sqlite3.Connection,
    source_id: int,
    operation: str,
    path: str,
    *,
    outcome: Literal["done", "failed"],
    target: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Record one change made (or attempted) on disk, and commit (along
    with anything the caller has pending): the record must survive
    whatever happens next."""
    with conn:
        conn.execute(
            "INSERT INTO file_changes (source_id, operation, path, target, outcome, error)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (source_id, operation, path, target, outcome, error),
        )


def change_file(
    conn: sqlite3.Connection,
    source_id: int,
    operation: str,
    path: str,
    change: Callable[[], object],
    *,
    target: Optional[str] = None,
) -> Optional[str]:
    """Make one change on disk and record it, done or failed; the error if
    it failed."""
    try:
        change()
    except OSError as exc:
        record_change(
            conn, source_id, operation, path, target=target, outcome="failed", error=str(exc)
        )
        return str(exc)
    record_change(conn, source_id, operation, path, target=target, outcome="done")
    return None
