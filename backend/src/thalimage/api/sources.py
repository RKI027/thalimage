"""Source folder management endpoints."""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse  # type: ignore[import-untyped]

from thalimage.deps import get_db, get_thumb_dir
from thalimage.services.scan_service import run_scan

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    path: str
    label: Optional[str] = None
    recursive: bool = True


class SourceResponse(BaseModel):
    id: int
    path: str
    label: Optional[str]
    recursive: bool
    enabled: bool
    created_at: str
    last_scan: Optional[str]


@router.get("", response_model=list[SourceResponse])
def list_sources(db: sqlite3.Connection = Depends(get_db)) -> list[SourceResponse]:
    rows = db.execute("SELECT * FROM sources ORDER BY label, path").fetchall()
    return [SourceResponse(**dict(r)) for r in rows]


@router.post("", response_model=SourceResponse, status_code=201)
def create_source(
    body: SourceCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> SourceResponse:
    source_path = Path(body.path).resolve()
    if not source_path.is_dir():
        raise HTTPException(400, f"Directory does not exist: {body.path}")

    try:
        cursor = db.execute(
            "INSERT INTO sources (path, label, recursive) VALUES (?, ?, ?)",
            (str(source_path), body.label, body.recursive),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Source path already exists") from exc

    row = db.execute("SELECT * FROM sources WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return SourceResponse(**dict(row))


@router.delete("/{source_id}", status_code=204)
def delete_source(
    source_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    cursor = db.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "Source not found")


@router.post("/{source_id}/scan")
def trigger_scan(
    source_id: int,
    db: sqlite3.Connection = Depends(get_db),
    thumb_dir: Path = Depends(get_thumb_dir),
) -> dict[str, object]:
    source = db.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if source is None:
        raise HTTPException(404, "Source not found")

    result = run_scan(db, source_id, thumb_dir)
    return result.model_dump()


@router.get("/{source_id}/scan/status")
async def scan_status_sse(
    source_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
) -> EventSourceResponse:
    """SSE endpoint for scan progress. Placeholder for async scan integration."""
    source = db.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if source is None:
        raise HTTPException(404, "Source not found")

    async def event_generator():  # type: ignore[no-untyped-def]
        yield {"event": "status", "data": '{"phase": "idle"}'}

    return EventSourceResponse(event_generator())
