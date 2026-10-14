"""Thalimage changes files only in sources marked writable, and only when
their folder really accepts writes; every change it makes is recorded."""

import errno
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from thalimage.services.file_changes import SourceNotWritable, record_change, writable_root


def _add(client: TestClient, folder: Path, **extra: object) -> dict:
    return client.post("/api/v1/sources", json={"path": str(folder), **extra}).json()


def _read_only_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> object:
        raise OSError(errno.EROFS, "Read-only file system")

    monkeypatch.setattr(tempfile, "mkstemp", refuse)


def test_a_new_source_is_read_only(client: TestClient, image_dir: Path) -> None:
    assert _add(client, image_dir)["writable"] is False


def test_a_source_can_be_created_writable(client: TestClient, image_dir: Path) -> None:
    assert _add(client, image_dir, writable=True)["writable"] is True


def test_a_source_can_be_switched_both_ways(client: TestClient, image_dir: Path) -> None:
    source_id = _add(client, image_dir)["id"]

    on = client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    assert on.status_code == 200 and on.json()["writable"] is True
    off = client.patch(f"/api/v1/sources/{source_id}", json={"writable": False})
    assert off.status_code == 200 and off.json()["writable"] is False


def test_switching_an_unknown_source_is_a_404(client: TestClient) -> None:
    assert client.patch("/api/v1/sources/999", json={"writable": True}).status_code == 404


def test_a_folder_that_refuses_writes_cannot_be_made_writable(
    client: TestClient, image_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _add(client, image_dir)["id"]
    _read_only_filesystem(monkeypatch)

    resp = client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})

    assert resp.status_code == 409
    assert "read-only" in resp.json()["detail"]
    assert client.get("/api/v1/sources").json()[0]["writable"] is False


def test_nor_created_writable(
    client: TestClient, image_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _read_only_filesystem(monkeypatch)

    resp = client.post("/api/v1/sources", json={"path": str(image_dir), "writable": True})

    assert resp.status_code == 409
    assert client.get("/api/v1/sources").json() == []


def test_checking_a_folder_leaves_nothing_behind(client: TestClient, image_dir: Path) -> None:
    before = sorted(image_dir.iterdir())
    _add(client, image_dir, writable=True)
    assert sorted(image_dir.iterdir()) == before


def _source(db: sqlite3.Connection, folder: Path, writable: bool) -> int:
    cursor = db.execute(
        "INSERT INTO sources (path, writable) VALUES (?, ?)", (str(folder), writable)
    )
    db.commit()
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def test_writable_root_refuses_a_read_only_source(db: sqlite3.Connection, tmp_path: Path) -> None:
    source_id = _source(db, tmp_path, writable=False)
    with pytest.raises(SourceNotWritable, match="not marked writable"):
        writable_root(db, source_id)


def test_writable_root_refuses_a_folder_that_refuses_writes(
    db: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _source(db, tmp_path, writable=True)
    _read_only_filesystem(monkeypatch)
    with pytest.raises(SourceNotWritable, match="read-only"):
        writable_root(db, source_id)


def test_writable_root_gives_the_folder_of_a_writable_source(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    source_id = _source(db, tmp_path, writable=True)
    assert writable_root(db, source_id) == tmp_path


def test_a_change_is_recorded_and_outlives_its_source(
    client: TestClient, db: sqlite3.Connection, image_dir: Path
) -> None:
    source_id = _add(client, image_dir, writable=True)["id"]
    record_change(db, source_id, "delete", "a.png", outcome="done")
    record_change(
        db, source_id, "rename", "b.jpg", target="c.jpg", outcome="failed", error="EACCES"
    )

    assert client.delete(f"/api/v1/sources/{source_id}").status_code == 204
    rows = db.execute(
        "SELECT source_id, operation, path, target, outcome, error FROM file_changes ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (source_id, "delete", "a.png", None, "done", None),
        (source_id, "rename", "b.jpg", "c.jpg", "failed", "EACCES"),
    ]
