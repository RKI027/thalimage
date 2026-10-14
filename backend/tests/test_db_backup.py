"""Tests for the database backup service."""

import asyncio
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from thalimage.db.engine import connect, migrate
from thalimage.services import db_backup
from thalimage.services.db_backup import (
    BackupConfig,
    BackupInProgress,
    BackupScheduler,
    next_run,
    read_config,
    read_last,
    take_backup,
    write_config,
)

NOW = datetime(2026, 10, 14, 6, 0, 0)


@pytest.fixture
def live_db(tmp_path: Path):
    """A migrated database with a row that so far lives only in the WAL."""
    path = tmp_path / "live" / "thalimage.db"
    path.parent.mkdir()
    conn = connect(path, check_same_thread=False)
    migrate(conn)
    conn.execute("PRAGMA wal_autocheckpoint=0")
    conn.execute("INSERT INTO settings (key, value) VALUES ('marker', 'in-wal')")
    conn.commit()
    yield path, conn
    conn.close()


def backup_names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


class TestTakeBackup:
    def test_copies_the_live_database_including_the_wal(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        target = take_backup(db_path, tmp_path / "backups", keep=7, now=NOW)

        copy = sqlite3.connect(target)
        try:
            value = copy.execute("SELECT value FROM settings WHERE key = 'marker'").fetchone()
            assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            copy.close()
        assert value == ("in-wal",)

    def test_names_the_copy_after_its_time(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        target = take_backup(db_path, tmp_path / "backups", keep=7, now=NOW)
        assert target == tmp_path / "backups" / "thalimage-20261014-060000.db"

    def test_creates_the_backup_folder(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        folder = tmp_path / "nested" / "backups"
        take_backup(db_path, folder, keep=7, now=NOW)
        assert folder.is_dir()

    def test_keeps_only_the_newest_copies(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        folder = tmp_path / "backups"
        folder.mkdir()
        for name in ("thalimage-20261011-060000.db", "thalimage-20261012-060000.db",
                     "thalimage-20261013-060000.db"):
            (folder / name).write_bytes(b"old")

        take_backup(db_path, folder, keep=2, now=NOW)

        assert backup_names(folder) == [
            "thalimage-20261013-060000.db",
            "thalimage-20261014-060000.db",
        ]

    def test_never_deletes_files_it_did_not_name(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        folder = tmp_path / "backups"
        folder.mkdir()
        for name in ("notes.txt", "thalimage-before-upgrade.db", "thalimage-20261013-060000.db"):
            (folder / name).write_bytes(b"x")

        take_backup(db_path, folder, keep=1, now=NOW)

        assert backup_names(folder) == [
            "notes.txt",
            "thalimage-20261014-060000.db",
            "thalimage-before-upgrade.db",
        ]

    def test_leaves_no_partial_file_when_the_copy_fails(
        self, live_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path, _ = live_db
        folder = tmp_path / "backups"

        def failing_copy(src: str, dst: str) -> None:
            Path(dst).write_bytes(b"half")
            raise OSError("disk full")

        monkeypatch.setattr(db_backup.shutil, "copyfile", failing_copy)
        with pytest.raises(OSError, match="disk full"):
            take_backup(db_path, folder, keep=7, now=NOW)
        assert backup_names(folder) == []


class TestNextRun:
    def test_later_today_when_the_time_is_still_ahead(self) -> None:
        assert next_run(datetime(2026, 10, 14, 5, 59), "06:00") == datetime(2026, 10, 14, 6, 0)

    def test_tomorrow_once_the_time_has_passed(self) -> None:
        assert next_run(datetime(2026, 10, 14, 6, 0), "06:00") == datetime(2026, 10, 15, 6, 0)
        assert next_run(datetime(2026, 10, 14, 23, 0), "06:00") == datetime(2026, 10, 15, 6, 0)


class TestConfig:
    def test_defaults(self, db: sqlite3.Connection) -> None:
        assert read_config(db) == BackupConfig(enabled=True, time="06:00", keep=7)

    def test_round_trips(self, db: sqlite3.Connection) -> None:
        write_config(db, enabled=False, time="23:30", keep=3)
        assert read_config(db) == BackupConfig(enabled=False, time="23:30", keep=3)

    def test_unset_fields_are_left_alone(self, db: sqlite3.Connection) -> None:
        write_config(db, keep=3)
        write_config(db, time="01:15")
        assert read_config(db) == BackupConfig(enabled=True, time="01:15", keep=3)

    @pytest.mark.parametrize("time", ["24:00", "6:00", "06:60", "noon"])
    def test_rejects_a_bad_time(self, time: str) -> None:
        with pytest.raises(ValidationError):
            BackupConfig(time=time)

    def test_rejects_keeping_nothing(self) -> None:
        with pytest.raises(ValidationError):
            BackupConfig(keep=0)


class TestScheduler:
    async def test_run_now_records_the_backup(self, live_db, tmp_path: Path) -> None:
        db_path, conn = live_db
        scheduler = BackupScheduler(db_path, tmp_path / "backups", clock=lambda: NOW)

        record = await scheduler.run_now()

        assert record.error is None
        assert record.file == "thalimage-20261014-060000.db"
        assert record.size == (tmp_path / "backups" / record.file).stat().st_size
        assert read_last(conn) == record

    async def test_run_now_records_a_failure(self, live_db, tmp_path: Path) -> None:
        db_path, conn = live_db
        blocker = tmp_path / "not-a-folder"
        blocker.write_text("x")
        scheduler = BackupScheduler(db_path, blocker / "backups", clock=lambda: NOW)

        record = await scheduler.run_now()

        assert record.file is None
        assert record.error
        assert read_last(conn) == record

    async def test_one_backup_at_a_time(
        self, live_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path, _ = live_db
        release = threading.Event()
        started = threading.Event()
        real_take = db_backup.take_backup

        def slow_take(*args, **kwargs):  # type: ignore[no-untyped-def]
            started.set()
            release.wait(5)
            return real_take(*args, **kwargs)

        monkeypatch.setattr(db_backup, "take_backup", slow_take)
        scheduler = BackupScheduler(db_path, tmp_path / "backups", clock=lambda: NOW)

        first = asyncio.create_task(scheduler.run_now())
        await asyncio.to_thread(started.wait, 5)
        assert scheduler.running
        with pytest.raises(BackupInProgress):
            await scheduler.run_now()
        release.set()
        assert (await first).error is None
        assert not scheduler.running

    def test_no_wait_when_disabled(self, live_db, tmp_path: Path) -> None:
        db_path, conn = live_db
        write_config(conn, enabled=False)
        scheduler = BackupScheduler(db_path, tmp_path / "backups", clock=lambda: NOW)
        assert scheduler.seconds_until_due() is None

    def test_waits_until_the_configured_time(self, live_db, tmp_path: Path) -> None:
        db_path, conn = live_db
        write_config(conn, time="07:30")
        scheduler = BackupScheduler(db_path, tmp_path / "backups", clock=lambda: NOW)
        assert scheduler.seconds_until_due() == 90 * 60


async def wait_for_backup(folder: Path, timeout: float = 3.0) -> bool:
    for _ in range(int(timeout / 0.02)):
        if folder.is_dir() and any(db_backup.BACKUP_NAME.match(p.name) for p in folder.iterdir()):
            return True
        await asyncio.sleep(0.02)
    return False



class TestScheduleLoop:
    async def test_backs_up_when_the_time_comes(self, live_db, tmp_path: Path) -> None:
        db_path, _ = live_db
        folder = tmp_path / "backups"
        scheduler = BackupScheduler(
            db_path, folder, clock=lambda: datetime(2026, 10, 14, 5, 59, 59, 900_000)
        )
        scheduler.start()
        try:
            assert await wait_for_backup(folder)
        finally:
            await scheduler.stop()

    async def test_picks_up_a_config_change_without_restarting(
        self, live_db, tmp_path: Path
    ) -> None:
        db_path, conn = live_db
        write_config(conn, enabled=False)
        folder = tmp_path / "backups"
        scheduler = BackupScheduler(
            db_path, folder, clock=lambda: datetime(2026, 10, 14, 5, 59, 59, 900_000)
        )
        scheduler.start()
        try:
            assert not await wait_for_backup(folder, timeout=0.3)
            write_config(conn, enabled=True)
            scheduler.config_changed()
            assert await wait_for_backup(folder)
        finally:
            await scheduler.stop()
