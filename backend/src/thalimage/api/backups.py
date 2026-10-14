"""Database backup endpoints: the schedule, the latest run, run-now."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from thalimage.deps import get_backup_scheduler, get_db
from thalimage.services import db_backup
from thalimage.services.db_backup import (
    BackupConfig,
    BackupInProgress,
    BackupRecord,
    BackupScheduler,
    CopiesKept,
    TimeOfDay,
)

router = APIRouter(prefix="/backups", tags=["backups"])


class BackupStatus(BaseModel):
    config: BackupConfig
    last: BackupRecord | None
    running: bool


class BackupConfigPatch(BaseModel):
    enabled: bool | None = None
    time: TimeOfDay | None = None
    keep: CopiesKept | None = None


def _status(db: sqlite3.Connection, scheduler: BackupScheduler) -> BackupStatus:
    return BackupStatus(
        config=db_backup.read_config(db),
        last=db_backup.read_last(db),
        running=scheduler.running,
    )


@router.get("", response_model=BackupStatus)
def read_backup_status(
    db: sqlite3.Connection = Depends(get_db),
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
) -> BackupStatus:
    return _status(db, scheduler)


@router.patch("", response_model=BackupStatus)
def patch_backup_config(
    body: BackupConfigPatch,
    db: sqlite3.Connection = Depends(get_db),
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
) -> BackupStatus:
    db_backup.write_config(db, enabled=body.enabled, time=body.time, keep=body.keep)
    scheduler.config_changed()
    return _status(db, scheduler)


@router.post("/run", response_model=BackupRecord)
async def run_backup_now(
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
) -> BackupRecord:
    try:
        return await scheduler.run_now()
    except BackupInProgress:
        raise HTTPException(409, "A backup is already running") from None
