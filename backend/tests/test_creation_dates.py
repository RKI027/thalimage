"""A known creation date survives rescans that cannot read one.

Linux reports no birth time, so a scan inside the container indexes
files with no creation date. That must never erase a date recorded
earlier (e.g. by a scan on macOS), and the earliest known date wins.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image

from thalimage.db.engine import connect, migrate
from thalimage.services import scan_service
from thalimage.services.scan_service import run_scan

KNOWN = "2020-01-01T00:00:00+00:00"


@pytest.fixture
def scanned(tmp_path: Path):
    """A source with one scanned image whose creation date is KNOWN."""
    conn = connect(tmp_path / "dates.db")
    migrate(conn)
    folder = tmp_path / "src"
    folder.mkdir()
    Image.new("RGB", (10, 10), "red").save(folder / "a.png")
    source_id = int(
        conn.execute("INSERT INTO sources (path) VALUES (?)", (str(folder),)).lastrowid  # type: ignore[arg-type]
    )
    conn.commit()
    thumbs = tmp_path / "thumbs"
    run_scan(conn, source_id, thumbs)
    conn.execute("UPDATE images SET file_created = ?", (KNOWN,))
    conn.execute("UPDATE image_locations SET file_created = ?", (KNOWN,))
    conn.commit()
    yield conn, source_id, folder, thumbs
    conn.close()


def birthtime(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    ts = datetime.fromisoformat(value).timestamp() if value else None
    monkeypatch.setattr(scan_service, "_birthtime", lambda stat: ts)


def created(conn: sqlite3.Connection) -> tuple[str | None, list[str | None]]:
    image = conn.execute("SELECT file_created FROM images").fetchone()[0]
    locations = [r[0] for r in conn.execute("SELECT file_created FROM image_locations")]
    return image, locations


def touch(path: Path) -> None:
    """Change the mtime so the next scan re-indexes the file."""
    later = datetime(2025, 6, 1, tzinfo=timezone.utc).timestamp()
    os.utime(path, (later, later))


def test_reindexing_without_a_birth_time_keeps_the_known_date(
    scanned, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn, source_id, folder, thumbs = scanned
    birthtime(monkeypatch, None)
    touch(folder / "a.png")

    run_scan(conn, source_id, thumbs)

    assert created(conn) == (KNOWN, [KNOWN])


def test_a_moved_file_keeps_its_creation_date(scanned, monkeypatch: pytest.MonkeyPatch) -> None:
    conn, source_id, folder, thumbs = scanned
    birthtime(monkeypatch, None)
    os.rename(folder / "a.png", folder / "renamed.png")

    run_scan(conn, source_id, thumbs)

    image, _ = created(conn)
    assert image == KNOWN


def test_a_later_birth_time_does_not_replace_an_earlier_date(
    scanned, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn, source_id, folder, thumbs = scanned
    birthtime(monkeypatch, "2024-03-01T00:00:00+00:00")
    touch(folder / "a.png")

    run_scan(conn, source_id, thumbs)

    assert created(conn) == (KNOWN, [KNOWN])


def test_an_earlier_birth_time_replaces_a_later_date(
    scanned, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn, source_id, folder, thumbs = scanned
    earlier = "2019-05-01T00:00:00+00:00"
    birthtime(monkeypatch, earlier)
    touch(folder / "a.png")

    run_scan(conn, source_id, thumbs)

    assert created(conn) == (earlier, [earlier])
