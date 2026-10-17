"""What a source holds: its files against its images, and why they differ."""

import sqlite3
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from thalimage.core.sidecars import digest, sidecars_of


class SourceFile(BaseModel):
    content_hash: str
    relative_path: str


class Sidecar(BaseModel):
    relative_path: str
    digest: str


class DuplicateGroup(BaseModel):
    """Files in one source with the same picture: one image. `sidecars`
    maps each path to its sidecars, whose digests tell which say the same.
    `file_hashes` maps each path to its file version (None until a scan has
    read it): copies with different versions differ in their metadata."""

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
    in their folder names."""

    files: int
    images: int
    duplicates: list[DuplicateGroup]
    archived: list[SourceFile]
    failures: list[ScanFailure]
    orphans: list[str]


def source_summary(conn: sqlite3.Connection, source_id: int) -> Optional[SourceSummary]:
    """None if the source does not exist."""
    source = conn.execute("SELECT path FROM sources WHERE id = ?", (source_id,)).fetchone()
    if source is None:
        return None
    root = Path(source["path"])
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

    return SourceSummary(
        files=len(locations),
        images=len(paths) - len(archived),
        duplicates=[
            DuplicateGroup(
                content_hash=h,
                paths=p,
                sidecars=_sidecars(root, p),
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
        orphans=[
            r["relative_path"]
            for r in conn.execute(
                "SELECT relative_path FROM sidecars"
                " WHERE source_id = ? AND orphan = 1 ORDER BY relative_path",
                (source_id,),
            )
        ],
    )


def _sidecars(root: Path, paths: list[str]) -> dict[str, list[Sidecar]]:
    found = {}
    for path in paths:
        sidecars = []
        for p in sidecars_of(root / path):
            try:
                sidecars.append(
                    Sidecar(relative_path=str(p.relative_to(root)), digest=digest(p))
                )
            except OSError:
                continue
        found[path] = sidecars
    return found
