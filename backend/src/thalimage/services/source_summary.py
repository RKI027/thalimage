"""What a source holds: its files against its images, and why they differ."""

import sqlite3
from pathlib import PurePath
from typing import Optional

from pydantic import BaseModel


class SourceFile(BaseModel):
    content_hash: str
    relative_path: str


class Sidecar(BaseModel):
    relative_path: str
    digest: str


class DuplicateGroup(BaseModel):
    """Files in one source with the same picture: one image. `sidecars`
    maps each path to its sidecars, with the digests the last scan read:
    those tell which copies say the same. `file_hashes` maps each path to
    its file version (None until a scan has read it): copies with different
    versions differ in their metadata."""

    content_hash: str
    paths: list[str]
    sidecars: dict[str, list[Sidecar]]
    file_hashes: dict[str, Optional[str]]


class ScanFailure(BaseModel):
    relative_path: str
    reason: str


class SourceSummary(BaseModel):
    """`files` are the files indexed in the source, `images` what browsing
    its preset shows. The difference is the extra copies in `duplicates`
    plus the `archived` images; `failures` were not indexed at all.
    `orphans` are the other files the last scan found that no media file
    in their folder names. `only_here` counts the images, archived ones
    included, that lie in no other source."""

    files: int
    images: int
    duplicates: list[DuplicateGroup]
    archived: list[SourceFile]
    failures: list[ScanFailure]
    orphans: list[str]
    only_here: int


def source_summary(conn: sqlite3.Connection, source_id: int) -> Optional[SourceSummary]:
    """None if the source does not exist."""
    source = conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone()
    if source is None:
        return None
    locations = conn.execute(
        "SELECT l.content_hash, l.relative_path, l.file_hash, i.archived FROM image_locations l"
        " JOIN images i ON i.content_hash = l.content_hash"
        " WHERE l.source_id = ? AND i.deleted = 0 ORDER BY l.relative_path",
        (source_id,),
    ).fetchall()

    paths: dict[str, list[str]] = {}
    for row in locations:
        paths.setdefault(row["content_hash"], []).append(row["relative_path"])
    archived = {row["content_hash"] for row in locations if row["archived"]}
    file_hashes = {row["relative_path"]: row["file_hash"] for row in locations}
    sidecar_rows = conn.execute(
        "SELECT relative_path, digest, orphan FROM sidecars"
        " WHERE source_id = ? ORDER BY relative_path",
        (source_id,),
    ).fetchall()

    return SourceSummary(
        files=len(locations),
        images=len(paths) - len(archived),
        duplicates=[
            DuplicateGroup(
                content_hash=h,
                paths=p,
                sidecars=_sidecars(sidecar_rows, p),
                file_hashes={path: file_hashes[path] for path in p},
            )
            for h, p in paths.items()
            if len(p) > 1
        ],
        archived=[
            SourceFile(content_hash=h, relative_path=p[0])
            for h, p in paths.items()
            if h in archived
        ],
        failures=[
            ScanFailure(relative_path=r["relative_path"], reason=r["reason"])
            for r in conn.execute(
                "SELECT relative_path, reason FROM scan_failures"
                " WHERE source_id = ? ORDER BY relative_path",
                (source_id,),
            )
        ],
        orphans=[r["relative_path"] for r in sidecar_rows if r["orphan"]],
        only_here=conn.execute(
            "SELECT COUNT(DISTINCT content_hash) FROM image_locations l WHERE source_id = ?"
            " AND NOT EXISTS (SELECT 1 FROM image_locations o"
            "   WHERE o.content_hash = l.content_hash AND o.source_id != l.source_id)",
            (source_id,),
        ).fetchone()[0],
    )


def _sidecars(rows: list[sqlite3.Row], paths: list[str]) -> dict[str, list[Sidecar]]:
    """Each path's sidecars, from the rows the last scan kept: a file in the
    media file's folder named after its stem (`img.txt`) or its whole name
    (`img.png.json`). Reading them all again, once per duplicate path, made
    the summary list and read the folder over and over."""
    by_folder: dict[str, dict[str, list[Sidecar]]] = {}
    for row in rows:
        if row["orphan"]:
            continue
        sidecar = PurePath(row["relative_path"])
        by_folder.setdefault(str(sidecar.parent), {}).setdefault(sidecar.stem, []).append(
            Sidecar(relative_path=row["relative_path"], digest=row["digest"])
        )
    found: dict[str, list[Sidecar]] = {}
    for path in paths:
        media = PurePath(path)
        names = by_folder.get(str(media.parent), {})
        sidecars = names.get(media.stem, []) + names.get(media.name, [])
        found[path] = sorted(sidecars, key=lambda s: PurePath(s.relative_path).name)
    return found
