"""Source folder management endpoints."""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse  # type: ignore[import-untyped]

from thalimage.db.engine import connect
from thalimage.deps import (
    get_db,
    get_preview_dir,
    get_scan_manager,
    get_thumb_dir,
    get_video_dir,
)
from thalimage.services.collection_service import get_or_create_source_preset
from thalimage.services.file_changes import SourceNotWritable, check_folder_accepts_writes
from thalimage.services.file_deletion import DeletionRefused, UnknownCopy, delete_copies
from thalimage.services.playable_copies import remove_playable_copies
from thalimage.services.scan_manager import ScanManager
from thalimage.services.scan_service import run_scan
from thalimage.services.source_service import delete_source, relabel_source
from thalimage.services.source_summary import SourceSummary, source_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


def _connection_db_path(conn: sqlite3.Connection) -> str:
    """Return the file path backing a SQLite connection's main database."""
    for _seq, name, file in conn.execute("PRAGMA database_list").fetchall():
        if name == "main":
            return str(file)
    raise RuntimeError("No main database found for connection")


def live_source(source_id: int, db: sqlite3.Connection = Depends(get_db)) -> sqlite3.Row:
    """The source a route names; 404 if there is none, or it was removed."""
    row: Optional[sqlite3.Row] = db.execute(
        "SELECT * FROM sources WHERE id = ? AND removed_at IS NULL", (source_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Source not found")
    return row


class SourceCreate(BaseModel):
    path: str
    label: Optional[str] = None
    recursive: bool = True
    writable: bool = False


class SourceUpdate(BaseModel):
    """Only the fields sent are changed; a blank or null label clears it."""

    writable: Optional[bool] = None
    rename_to_hash: Optional[bool] = None
    label: Optional[str] = None


class CopiesToDelete(BaseModel):
    paths: list[str]


class DeleteFailure(BaseModel):
    relative_path: str
    error: str


class DeletedCopies(BaseModel):
    deleted: list[str]
    sidecars: list[str]
    failed: list[DeleteFailure]


class SourceResponse(BaseModel):
    id: int
    path: str
    label: Optional[str]
    recursive: bool
    enabled: bool
    writable: bool
    rename_to_hash: bool
    created_at: str
    last_scan: Optional[str]


@router.get("", response_model=list[SourceResponse])
def list_sources(db: sqlite3.Connection = Depends(get_db)) -> list[SourceResponse]:
    rows = db.execute(
        "SELECT * FROM sources WHERE removed_at IS NULL ORDER BY label, path"
    ).fetchall()
    return [SourceResponse(**dict(r)) for r in rows]


@router.post("", response_model=SourceResponse, status_code=201)
def create_source(
    body: SourceCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> SourceResponse:
    source_path = Path(body.path).resolve()
    if not source_path.is_dir():
        raise HTTPException(400, f"Directory does not exist: {body.path}")
    if body.writable:
        _require_writes(source_path)

    # A folder removed with its images' data kept comes back as the same
    # source, settings reset; a live one is refused.
    cursor = db.execute(
        """INSERT INTO sources (path, label, recursive, writable) VALUES (?, ?, ?, ?)
           ON CONFLICT(path) DO UPDATE SET
            label = excluded.label, recursive = excluded.recursive,
            writable = excluded.writable, rename_to_hash = 0, enabled = 1,
            created_at = datetime('now'), last_scan = NULL, removed_at = NULL
           WHERE removed_at IS NOT NULL""",
        (str(source_path), body.label, body.recursive, body.writable),
    )
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(409, "Source path already exists")

    row = db.execute("SELECT * FROM sources WHERE path = ?", (str(source_path),)).fetchone()
    source = SourceResponse(**dict(row))
    get_or_create_source_preset(db, source.id, body.label or source_path.name)
    return source


def _require_writes(folder: Path) -> None:
    try:
        check_folder_accepts_writes(folder)
    except SourceNotWritable as exc:
        raise HTTPException(409, str(exc)) from exc


@router.patch("/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: int,
    body: SourceUpdate,
    row: sqlite3.Row = Depends(live_source),
    db: sqlite3.Connection = Depends(get_db),
) -> SourceResponse:
    """Relabel a source, mark it writable (once its folder has accepted a
    test write) or read-only, which stops renaming its files, or have its
    scans rename its files to their picture hash (writable sources only)."""
    writable = row["writable"] if body.writable is None else body.writable
    if body.rename_to_hash and not writable:
        raise HTTPException(409, "Only a writable source can rename its files.")
    if body.writable is not None:
        if body.writable:
            _require_writes(Path(row["path"]))
        db.execute("UPDATE sources SET writable = ? WHERE id = ?", (body.writable, source_id))
    if not writable or body.rename_to_hash is not None:
        db.execute(
            "UPDATE sources SET rename_to_hash = ? WHERE id = ?",
            (bool(writable and body.rename_to_hash), source_id),
        )
    db.commit()
    if "label" in body.model_fields_set:
        relabel_source(db, source_id, body.label)
    row = db.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    return SourceResponse(**dict(row))


@router.delete("/{source_id}", status_code=204, dependencies=[Depends(live_source)])
def del_source(
    source_id: int,
    keep_data: bool = True,
    db: sqlite3.Connection = Depends(get_db),
    video_dir: Path = Depends(get_video_dir),
) -> None:
    """Remove a source. Its images found nowhere else keep their data
    unless `keep_data` is false."""
    removed = delete_source(db, source_id, keep_data=keep_data)
    if removed is None:
        raise HTTPException(404, "Source not found")
    remove_playable_copies(video_dir, removed)


@router.post(
    "/{source_id}/delete-copies", response_model=DeletedCopies, dependencies=[Depends(live_source)]
)
def delete_source_copies(
    source_id: int,
    body: CopiesToDelete,
    db: sqlite3.Connection = Depends(get_db),
) -> DeletedCopies:
    """Delete files from disk that are copies of an image kept elsewhere.
    Refused as a whole if any of them may not be deleted."""
    try:
        result = delete_copies(db, source_id, body.paths)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except UnknownCopy as exc:
        raise HTTPException(400, str(exc)) from exc
    except (SourceNotWritable, DeletionRefused) as exc:
        raise HTTPException(409, str(exc)) from exc
    return DeletedCopies(
        deleted=result.deleted,
        sidecars=result.sidecars,
        failed=[DeleteFailure(relative_path=p, error=e) for _, p, e in result.failed],
    )


@router.get(
    "/{source_id}/summary", response_model=SourceSummary, dependencies=[Depends(live_source)]
)
def get_source_summary(
    source_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> SourceSummary:
    summary = source_summary(db, source_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return summary


@router.post("/{source_id}/scan", status_code=202, dependencies=[Depends(live_source)])
async def trigger_scan(
    source_id: int,
    db: sqlite3.Connection = Depends(get_db),
    thumb_dir: Path = Depends(get_thumb_dir),
    preview_dir: Path = Depends(get_preview_dir),
    video_dir: Path = Depends(get_video_dir),
    scan_manager: ScanManager = Depends(get_scan_manager),
) -> dict[str, str]:
    if not scan_manager.can_start(source_id):
        raise HTTPException(409, "Scan already running for this source")

    scan_manager.start(source_id)

    # The scan runs in a worker thread; give it its own connection rather than
    # sharing the request connection (a single sqlite3.Connection is not safe
    # for concurrent use across threads). WAL mode makes its commits visible to
    # the request connections.
    db_path = Path(_connection_db_path(db))

    def do_scan() -> None:
        worker_conn = connect(db_path, check_same_thread=False)
        try:
            def on_progress(**kwargs: object) -> None:
                scan_manager.update(source_id, **kwargs)

            result = run_scan(
                worker_conn,
                source_id,
                thumb_dir,
                preview_dir=preview_dir,
                video_dir=video_dir,
                progress_callback=on_progress,
            )
            scan_manager.complete(
                source_id,
                added=result.added,
                skipped=result.skipped,
                errors=result.errors,
                sidecars_added=result.sidecars_added,
                sidecars_changed=result.sidecars_changed,
                sidecars_removed=result.sidecars_removed,
                renamed=result.renamed,
            )
        except Exception as exc:
            logger.exception("Scan of source %d failed", source_id)
            scan_manager.fail(source_id, message=str(exc))
        finally:
            worker_conn.close()

    asyncio.get_running_loop().run_in_executor(None, do_scan)
    return {"status": "started"}


@router.get("/{source_id}/scan/status", dependencies=[Depends(live_source)])
async def scan_status_sse(
    source_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    scan_manager: ScanManager = Depends(get_scan_manager),
) -> EventSourceResponse:
    async def event_generator():  # type: ignore[no-untyped-def]
        progress = scan_manager.get_progress(source_id)
        if progress is None:
            yield {"event": "status", "data": json.dumps({"phase": "idle"})}
            return

        while not await request.is_disconnected():
            yield {"event": "status", "data": progress.model_dump_json()}
            if progress.phase in ("complete", "error"):
                return
            progress = await scan_manager.wait_for_update(source_id, timeout=2.0)
            if progress is None:
                return

    return EventSourceResponse(event_generator())
