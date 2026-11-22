"""Moving files from one source to another (#180).

A file takes the same relative path under the target source's folder,
created if need be. A path the target already uses is resolved as a rename
is: the copy is redundant when the target holds this image there, it takes
the image's hash name when that is free, and the move is refused when it
is not. Sidecars follow their file.
"""

import errno
import logging
import os
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from thalimage.core.sidecars import claimed, digest, renamed_for, sidecars_of
from thalimage.services.file_access import describe, read_error
from thalimage.services.file_changes import (
    change_file,
    location_row,
    record_change,
    still_as_scanned,
    writable_root,
)
from thalimage.services.file_deletion import UnknownCopy, remove_copy
from thalimage.services.locations import sync_images

logger = logging.getLogger(__name__)


class MoveRefused(Exception):
    """Moving would act on a file the index no longer describes, or replace
    another file."""


@dataclass
class MoveResult:
    moved: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # the target already held the image
    sidecars: list[str] = field(default_factory=list)  # moved along
    kept_sidecars: list[str] = field(default_factory=list)  # left behind
    failed: list[tuple[int, str, str]] = field(default_factory=list)  # (source, path, error)
    # Moved, but the app cannot read them there: a share the new folder's
    # permissions refuse, which the move itself cannot see coming.
    not_readable: list[tuple[int, str, str]] = field(default_factory=list)


@dataclass
class _Copy:
    source_id: int
    root: Path
    path: str
    to_source_id: int
    to_root: Path
    target: str  # relative to the target source
    left_behind: bool  # the target already holds the image at `target`
    content_hash: str
    location: sqlite3.Row


def move_copies(
    conn: sqlite3.Connection, source_id: int, to_source_id: int, paths: list[str]
) -> MoveResult:
    """Move these files (relative to the source) into the folder of another
    source, keeping their relative paths.

    Everything is checked before anything is moved: both sources must be
    writable (LookupError, SourceNotWritable), each path an indexed file of
    the source (UnknownCopy), no file changed since it was scanned, and the
    target must not hold a different file at any destination (MoveRefused).
    A move that then fails is reported in the result; every attempt is
    recorded.
    """
    if source_id == to_source_id:
        raise MoveRefused("A file cannot be moved to its own source.")
    if conn.execute(
        "SELECT 1 FROM sources WHERE id = ? AND removed_at IS NULL", (to_source_id,)
    ).fetchone() is None:
        raise LookupError(f"Source {to_source_id} not found")
    root = writable_root(conn, source_id)
    to_root = writable_root(conn, to_source_id)

    targets = [
        _resolve(conn, source_id, root, to_source_id, to_root, path)
        for path in dict.fromkeys(paths)
    ]
    for t in targets:
        if not still_as_scanned(conn, t.source_id, t.root, t.path, t.location):
            raise MoveRefused(f"{t.path} changed since the last scan; rescan first.")
    destinations = [t.target for t in targets if not t.left_behind]
    if len(set(destinations)) < len(destinations):
        raise MoveRefused("Two files would take the same path in the target.")

    result = MoveResult()
    for t in targets:
        _move(conn, t, result)
    return result


def _resolve(
    conn: sqlite3.Connection,
    source_id: int,
    root: Path,
    to_source_id: int,
    to_root: Path,
    path: str,
) -> _Copy:
    """Where the file goes, refusing a destination another file holds."""
    row = location_row(conn, source_id, path)
    if row is None:
        raise UnknownCopy(f"{path} is not an indexed file of this source.")
    content_hash = row["content_hash"]

    def copy(target: str, left_behind: bool) -> _Copy:
        return _Copy(
            source_id, root, path, to_source_id, to_root, target, left_behind,
            content_hash, row,
        )

    holder = _indexed(conn, to_source_id, path)
    if (to_root / path).exists():
        if holder is not None and holder["content_hash"] == content_hash:
            return copy(path, True)
        # The name is taken by something else: the file goes by its hash
        # name, as renaming does, or not at all.
        path_hash = str(PurePath(path).with_name(content_hash + PurePath(path).suffix))
        if (to_root / path_hash).exists() or _indexed(conn, to_source_id, path_hash) is not None:
            raise MoveRefused(f"{path_hash} already exists in the target; {path} cannot move.")
        return copy(path_hash, False)
    if holder is not None:
        raise MoveRefused(f"{path} is indexed in the target but its file is gone; rescan first.")
    return copy(path, False)


def _indexed(conn: sqlite3.Connection, source_id: int, path: str) -> sqlite3.Row | None:
    return location_row(conn, source_id, path)


def _move(conn: sqlite3.Connection, t: _Copy, result: MoveResult) -> None:
    """Move one file, or drop it when the target already holds the image."""
    media = t.root / t.path
    sidecars = sidecars_of(media)
    if t.left_behind:
        error = remove_copy(conn, t.source_id, t.root, t.path)
        if error is not None:
            result.failed.append((t.source_id, t.path, error))
            return
        result.deleted.append(t.path)
    else:
        target = t.to_root / t.target
        error = _make_parent(target)
        if error is None:
            error = change_file(
                conn, t.source_id, "move", t.path,
                lambda: _transfer(media, target),
                target=t.target, target_source_id=t.to_source_id,
            )
        else:
            record_change(
                conn, t.source_id, "move", t.path, target=t.target,
                target_source_id=t.to_source_id, outcome="failed", error=error,
            )
        if error is not None:
            result.failed.append((t.source_id, t.path, error))
            return
        _move_location(conn, t)
        result.moved.append(t.path)
        _check_readable(t, target, result)
    for sidecar in sidecars:
        if not claimed(sidecar):
            _follow(conn, t, media, sidecar, result)


def _check_readable(t: _Copy, target: Path, result: MoveResult) -> None:
    """Report a file that arrived but that the app may not read: a share
    can apply its own permissions to what lands in it, and nothing else
    notices until someone opens the image."""
    error = read_error(str(target))
    if error is None:
        return
    reason = describe(error)
    logger.warning(
        "Moved %s to %s, but cannot read it there: %s", t.root / t.path, target, reason
    )
    result.not_readable.append((t.source_id, t.path, reason))


def _make_parent(target: Path) -> str | None:
    """Create the target's folder, if the source's folders have not been;
    the error if that fails."""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return str(exc)
    return None


def _transfer(source: Path, target: Path) -> None:
    """Move one file, between filesystems too: the copy is made under a
    temporary name and put in place before the source is removed, so no
    file is ever lost or left half-written under its name."""
    try:
        os.rename(source, target)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        temporary = target.with_name(f".{target.name}.thalimage-move")
        try:
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        os.unlink(source)


def _move_location(conn: sqlite3.Connection, t: _Copy) -> None:
    """Point the copy's location, and its image if opened from it, at the
    target source."""
    name = PurePath(t.target).name
    with conn:
        conn.execute(
            "UPDATE image_locations SET source_id = ?, relative_path = ?, filename = ?"
            " WHERE source_id = ? AND relative_path = ?",
            (t.to_source_id, t.target, name, t.source_id, t.path),
        )
        sync_images(conn, [t.content_hash])


def _follow(
    conn: sqlite3.Connection, t: _Copy, media: Path, sidecar: Path, result: MoveResult
) -> None:
    """Move a sidecar along, named after its file. One whose destination is
    taken is deleted if it says the same as the file there, else left in
    place as an orphan."""
    path = str(sidecar.relative_to(t.root))
    target = str(
        PurePath(t.target).with_name(renamed_for(media, sidecar, PurePath(t.target).name))
    )
    destination = t.to_root / target
    error = _make_parent(destination)
    if error is not None:
        result.failed.append((t.source_id, path, error))
        return

    if not destination.exists():
        error = change_file(
            conn, t.source_id, "move", path,
            lambda: _transfer(sidecar, destination),
            target=target, target_source_id=t.to_source_id,
        )
        if error is None:
            with conn:
                conn.execute(
                    "UPDATE sidecars SET source_id = ?, relative_path = ?, orphan = 0"
                    " WHERE source_id = ? AND relative_path = ?",
                    (t.to_source_id, target, t.source_id, path),
                )
            result.sidecars.append(path)
        else:
            result.failed.append((t.source_id, path, error))
    elif digest(destination) == digest(sidecar):
        error = change_file(
            conn, t.source_id, "delete", path, lambda: os.remove(sidecar)
        )
        if error is None:
            with conn:
                conn.execute(
                    "DELETE FROM sidecars WHERE source_id = ? AND relative_path = ?",
                    (t.source_id, path),
                )
            result.sidecars.append(path)
        else:
            result.failed.append((t.source_id, path, error))
    else:
        with conn:
            conn.execute(
                "UPDATE sidecars SET orphan = 1 WHERE source_id = ? AND relative_path = ?",
                (t.source_id, path),
            )
        result.kept_sidecars.append(path)
