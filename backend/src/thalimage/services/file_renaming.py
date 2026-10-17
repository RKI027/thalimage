"""Renaming image files to their picture hash (#14).

A file keeps its folder and extension and takes its image's key as its
name. A copy whose folder already holds the image under that name is
redundant: it is deleted instead, its metadata staying in file_metadata.
Sidecars follow their file's new name.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from thalimage.core.sidecars import claimed, digest, sidecars_of
from thalimage.services.file_changes import change_file, record_change, writable_root
from thalimage.services.file_deletion import image_copies, remove_copy
from thalimage.services.scan_service import unchanged_since_scan


class RenameRefused(Exception):
    """Renaming would act on a file the index no longer describes, or
    replace another file."""


@dataclass
class RenameResult:
    renamed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # redundant copies
    kept_sidecars: list[str] = field(default_factory=list)  # left where they were
    failed: list[tuple[int, str, str]] = field(default_factory=list)  # (source, path, error)


@dataclass
class _Copy:
    source_id: int
    root: Path
    path: str
    content_hash: str

    @property
    def target(self) -> str:
        """The path the file takes: its image's key, in its folder, with
        its extension."""
        path = PurePath(self.path)
        return str(path.with_name(self.content_hash + path.suffix))


_LOCATION = (
    "SELECT content_hash, file_modified, file_size FROM image_locations"
    " WHERE source_id = ? AND relative_path = ?"
)


def rename_image(conn: sqlite3.Connection, content_hash: str) -> RenameResult | None:
    """Rename every copy of a live image, in every source, to its picture
    hash; None if there is no such image.

    Refused as a whole unless every source holding a copy is writable
    (SourceNotWritable), no copy changed since it was scanned and no hash
    name is taken by another file (RenameRefused). A rename that then
    fails is reported in the result; every attempt is recorded.
    """
    copies = image_copies(conn, content_hash)
    if copies is None:
        return None
    roots = {c.source_id: writable_root(conn, c.source_id) for c in copies}
    targets = [
        _Copy(c.source_id, roots[c.source_id], c.relative_path, content_hash) for c in copies
    ]
    for t in targets:
        refusal = _refusal(conn, t)
        if refusal is not None:
            raise RenameRefused(refusal)

    result = RenameResult()
    for t in targets:
        _rename(conn, t, result)
    return result


def rename_source_files(conn: sqlite3.Connection, source_id: int) -> RenameResult:
    """Rename every file of a writable source to its picture hash, as
    rename_image does a copy. A file that may not be renamed is reported in
    the result, with why, and the others are renamed. LookupError,
    SourceNotWritable as for writable_root."""
    root = writable_root(conn, source_id)
    rows = conn.execute(
        "SELECT relative_path, content_hash FROM image_locations"
        " WHERE source_id = ? ORDER BY relative_path",
        (source_id,),
    ).fetchall()
    result = RenameResult()
    for row in rows:
        t = _Copy(source_id, root, row["relative_path"], row["content_hash"])
        refusal = _refusal(conn, t)
        if refusal is not None:
            result.failed.append((source_id, t.path, refusal))
            continue
        _rename(conn, t, result)
    return result


def _refusal(conn: sqlite3.Connection, t: _Copy) -> str | None:
    """Why the copy may not be renamed, if it may not."""
    if t.path == t.target:
        return None
    location = conn.execute(_LOCATION, (t.source_id, t.path)).fetchone()
    try:
        unchanged = unchanged_since_scan((t.root / t.path).stat(), location)
    except FileNotFoundError:
        unchanged = False
    if not unchanged:
        return f"{t.path} changed since the last scan; rescan first."
    if (t.root / t.target).exists() and not _holds_image(conn, t):
        return f"{t.target} already exists and is not a copy of this image."
    return None


def _holds_image(conn: sqlite3.Connection, t: _Copy) -> bool:
    """Whether the copy's hash name is an indexed copy of its image."""
    row = conn.execute(_LOCATION, (t.source_id, t.target)).fetchone()
    return row is not None and row["content_hash"] == t.content_hash


def _rename(conn: sqlite3.Connection, t: _Copy, result: RenameResult) -> None:
    """Rename one copy, or delete it when its folder already holds the
    image under its hash name; then move its sidecars along."""
    if t.path == t.target:
        return
    media = t.root / t.path
    sidecars = sidecars_of(media)
    if not (t.root / t.target).exists():
        error = change_file(
            conn, t.source_id, "rename", t.path,
            lambda: os.rename(media, t.root / t.target), target=t.target,
        )
        if error is None:
            _move_location(conn, t)
            result.renamed.append(t.path)
    elif _holds_image(conn, t):
        error = remove_copy(conn, t.source_id, t.root, t.path)
        if error is None:
            result.deleted.append(t.path)
    else:
        error = f"{t.target} already exists and is not a copy of this image."
        record_change(
            conn, t.source_id, "rename", t.path, target=t.target, outcome="failed", error=error
        )
    if error is not None:
        result.failed.append((t.source_id, t.path, error))
        return
    for sidecar in sidecars:
        if not claimed(sidecar):
            _follow(conn, t, media, sidecar, result)


def _move_location(conn: sqlite3.Connection, t: _Copy) -> None:
    """Point the copy's location, and its image if opened from it, at the
    new name."""
    name = PurePath(t.target).name
    with conn:
        conn.execute(
            "UPDATE image_locations SET relative_path = ?, filename = ?"
            " WHERE source_id = ? AND relative_path = ?",
            (t.target, name, t.source_id, t.path),
        )
        conn.execute(
            "UPDATE images SET relative_path = ?, filename = ?"
            " WHERE content_hash = ? AND source_id = ? AND relative_path = ?",
            (t.target, name, t.content_hash, t.source_id, t.path),
        )


def _follow(
    conn: sqlite3.Connection, t: _Copy, media: Path, sidecar: Path, result: RenameResult
) -> None:
    """Give a sidecar its file's new name. One whose new name is taken is
    deleted if it says the same as the file there, else left in place."""
    # "img.png.json" is named after the whole file name, "img.txt" after its stem.
    renamed = PurePath(t.target)
    if sidecar.stem == media.name:
        new_name = renamed.name + sidecar.name[len(media.name):]
    else:
        new_name = renamed.stem + sidecar.name[len(media.stem):]
    path = str(sidecar.relative_to(t.root))
    target = str(PurePath(path).with_name(new_name))

    if not (t.root / target).exists():
        error = change_file(
            conn, t.source_id, "rename", path,
            lambda: os.rename(sidecar, t.root / target), target=target,
        )
        update = "UPDATE sidecars SET relative_path = ?, orphan = 0"
        params: tuple[object, ...] = (target,)
    elif digest(t.root / target) == digest(sidecar):
        error = change_file(conn, t.source_id, "delete", path, lambda: os.remove(sidecar))
        update, params = "DELETE FROM sidecars", ()
    else:
        result.kept_sidecars.append(path)
        error = None
        update, params = "UPDATE sidecars SET orphan = 1", ()
    if error is not None:
        result.failed.append((t.source_id, path, error))
        return
    with conn:
        conn.execute(
            update + " WHERE source_id = ? AND relative_path = ?", (*params, t.source_id, path)
        )
