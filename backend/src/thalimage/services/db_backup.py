"""Daily copies of the database, kept in a folder beside the caches.

The database must live on local disk (SQLite's WAL does not work over a
network filesystem); its backups can go anywhere, NFS included. A copy is
taken through SQLite's backup API into a local temporary file, then copied
to the backup folder under a temporary name and renamed into place, so a
half-written file never looks like a backup and no SQLite database is ever
opened on the backup folder's filesystem.
"""

import asyncio
import json
import logging
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from thalimage.db.engine import BUSY_TIMEOUT_S, connect

logger = logging.getLogger(__name__)

BACKUP_NAME = re.compile(r"^thalimage-\d{8}-\d{6}\.db$")
CONFIG_KEYS = {"enabled": "backup_enabled", "time": "backup_time", "keep": "backup_keep"}
LAST_KEY = "backup_last"


# Local time of day, HH:MM, in the process's time zone (TZ).
TimeOfDay = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
CopiesKept = Annotated[int, Field(ge=1)]


class BackupConfig(BaseModel):
    enabled: bool = True
    time: TimeOfDay = "06:00"
    keep: CopiesKept = 7


class BackupRecord(BaseModel):
    """The outcome of the latest backup run: a file, or an error."""

    at: str
    file: str | None = None
    size: int | None = None
    error: str | None = None


class BackupInProgress(Exception):
    """A backup was requested while another one was still running."""


def read_config(conn: sqlite3.Connection) -> BackupConfig:
    stored = {
        r["key"]: r["value"]
        for r in conn.execute(
            "SELECT key, value FROM settings WHERE key IN (?, ?, ?)", tuple(CONFIG_KEYS.values())
        )
    }
    values: dict[str, object] = {}
    if CONFIG_KEYS["enabled"] in stored:
        values["enabled"] = stored[CONFIG_KEYS["enabled"]] == "true"
    if CONFIG_KEYS["time"] in stored:
        values["time"] = stored[CONFIG_KEYS["time"]]
    if CONFIG_KEYS["keep"] in stored:
        values["keep"] = int(stored[CONFIG_KEYS["keep"]])
    return BackupConfig.model_validate(values)


def write_config(
    conn: sqlite3.Connection,
    *,
    enabled: bool | None = None,
    time: str | None = None,
    keep: int | None = None,
) -> BackupConfig:
    """Store the given fields (None leaves one unchanged), validated, and commit."""
    changes = {k: v for k, v in (("enabled", enabled), ("time", time), ("keep", keep)) if v is not None}
    config = BackupConfig.model_validate({**read_config(conn).model_dump(), **changes})
    for field in changes:
        value = getattr(config, field)
        text = ("true" if value else "false") if isinstance(value, bool) else str(value)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (CONFIG_KEYS[field], text),
        )
    conn.commit()
    return config


def read_last(conn: sqlite3.Connection) -> BackupRecord | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (LAST_KEY,)).fetchone()
    return BackupRecord(**json.loads(row["value"])) if row else None


def record_last(conn: sqlite3.Connection, record: BackupRecord) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (LAST_KEY, record.model_dump_json()),
    )
    conn.commit()


def take_backup(db_path: Path, backup_dir: Path, *, keep: int, now: datetime) -> Path:
    """Copy the live database into `backup_dir`, then drop all but the
    newest `keep` copies. Returns the new copy's path."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"thalimage-{now:%Y%m%d-%H%M%S}.db"
    partial = backup_dir / f".{target.name}.partial"
    with tempfile.TemporaryDirectory() as scratch:
        snapshot = Path(scratch) / "snapshot.db"
        source = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_S)
        dest = sqlite3.connect(snapshot)
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
        try:
            shutil.copyfile(snapshot, partial)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)

    copies = sorted(p for p in backup_dir.iterdir() if BACKUP_NAME.match(p.name))
    for stale in copies[:-keep]:
        stale.unlink()
    return target


def next_run(now: datetime, time: str) -> datetime:
    """The next moment strictly after `now` whose wall-clock time is `time`."""
    hour, minute = (int(part) for part in time.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


class BackupScheduler:
    """Takes a backup at the configured time each day, and on request.

    One backup runs at a time. A run missed while the app was down is not
    made up: the next one happens at the next configured time.
    """

    def __init__(
        self,
        db_path: Path,
        backup_dir: Path,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._db_path = db_path
        self._backup_dir = backup_dir
        self._clock = clock
        self._running = False
        self._config_changed = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    def _read(self) -> tuple[BackupConfig, BackupRecord | None]:
        conn = connect(self._db_path)
        try:
            return read_config(conn), read_last(conn)
        finally:
            conn.close()

    def status(self) -> tuple[BackupConfig, BackupRecord | None]:
        return self._read()

    def seconds_until_due(self) -> float | None:
        """How long until the next scheduled backup; None when disabled."""
        config, _ = self._read()
        if not config.enabled:
            return None
        now = self._clock()
        return (next_run(now, config.time) - now).total_seconds()

    def config_changed(self) -> None:
        """Re-read the schedule now rather than at the next wake-up."""
        self._config_changed.set()

    async def run_now(self) -> BackupRecord:
        if self._running:
            raise BackupInProgress
        self._running = True
        try:
            return await asyncio.to_thread(self._backup)
        finally:
            self._running = False

    def _backup(self) -> BackupRecord:
        now = self._clock()
        conn = connect(self._db_path)
        try:
            config = read_config(conn)
            try:
                target = take_backup(self._db_path, self._backup_dir, keep=config.keep, now=now)
                record = BackupRecord(
                    at=now.isoformat(), file=target.name, size=target.stat().st_size
                )
            except Exception as exc:
                logger.exception("Database backup failed")
                record = BackupRecord(at=now.isoformat(), error=str(exc) or type(exc).__name__)
            record_last(conn, record)
            return record
        finally:
            conn.close()

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            delay = await asyncio.to_thread(self.seconds_until_due)
            self._config_changed.clear()
            try:
                # None (disabled) waits for a config change only.
                await asyncio.wait_for(self._config_changed.wait(), timeout=delay)
                continue
            except TimeoutError:
                pass
            try:
                await self.run_now()
            except BackupInProgress:
                pass
