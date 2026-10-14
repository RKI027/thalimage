"""Deleting copies of an image from disk: only in a writable source, never
the last copy of an image, never a file that changed since it was
scanned, and every attempt recorded."""

import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers import scan_source

COPY = str(Path("sub") / "a-copy.png")


@pytest.fixture
def duplicated(client: TestClient, image_dir: Path) -> tuple[int, str]:
    """A writable source where a.png has a copy, sub/a-copy.png."""
    shutil.copy(image_dir / "a.png", image_dir / COPY)
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    [group] = client.get(f"/api/v1/sources/{source_id}/summary").json()["duplicates"]
    return source_id, group["content_hash"]


def _delete(client: TestClient, source_id: int, *paths: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/sources/{source_id}/delete-copies", json={"paths": list(paths)})


def _changes(db: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return [
        tuple(r) for r in db.execute("SELECT operation, path, outcome FROM file_changes ORDER BY id")
    ]


def test_deleting_a_copy_removes_the_file_and_keeps_the_image(
    client: TestClient, db: sqlite3.Connection, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, content_hash = duplicated

    resp = _delete(client, source_id, COPY)

    assert resp.status_code == 200
    assert resp.json() == {"deleted": [COPY], "sidecars": [], "failed": []}
    assert not (image_dir / COPY).exists()
    assert (image_dir / "a.png").exists()
    assert client.get(f"/api/v1/sources/{source_id}/summary").json()["duplicates"] == []
    assert client.get(f"/api/v1/images/{content_hash}").status_code == 200
    assert _changes(db) == [("delete", COPY, "done")]


def test_deleting_the_copy_an_image_opens_from_moves_it_to_another(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, content_hash = duplicated

    _delete(client, source_id, "a.png")

    assert client.get(f"/api/v1/images/{content_hash}").json()["relative_path"] == COPY
    assert client.get(f"/api/v1/images/{content_hash}/file").status_code == 200


def test_a_read_only_source_is_refused(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": False})

    resp = _delete(client, source_id, COPY)

    assert resp.status_code == 409
    assert "not marked writable" in resp.json()["detail"]
    assert (image_dir / COPY).exists()


def test_the_last_copy_of_an_image_is_refused(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated

    resp = _delete(client, source_id, "b.jpg")

    assert resp.status_code == 409
    assert "only copy" in resp.json()["detail"]
    assert (image_dir / "b.jpg").exists()


def test_every_copy_at_once_is_refused_and_nothing_is_deleted(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated

    resp = _delete(client, source_id, "a.png", COPY)

    assert resp.status_code == 409
    assert (image_dir / "a.png").exists() and (image_dir / COPY).exists()


def test_a_path_that_is_not_an_indexed_copy_is_refused(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated

    for path in ("readme.txt", "missing.png", "../images/a.png"):
        resp = _delete(client, source_id, path)
        assert resp.status_code == 400, path
    assert (image_dir / "readme.txt").exists()


def test_a_file_changed_since_the_scan_is_refused(
    client: TestClient, image_dir: Path, duplicated: tuple[int, str]
) -> None:
    source_id, _ = duplicated
    st = (image_dir / COPY).stat()
    os.utime(image_dir / COPY, (st.st_atime, st.st_mtime + 60))

    resp = _delete(client, source_id, COPY)

    assert resp.status_code == 409
    assert "rescan" in resp.json()["detail"]
    assert (image_dir / COPY).exists()


def test_a_failed_removal_is_reported_and_recorded(
    client: TestClient,
    db: sqlite3.Connection,
    image_dir: Path,
    duplicated: tuple[int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, _ = duplicated

    def refuse(path: object) -> None:
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(os, "remove", refuse)
    resp = _delete(client, source_id, COPY)

    assert resp.status_code == 200
    [failure] = resp.json()["failed"]
    assert failure["relative_path"] == COPY and "Permission denied" in failure["error"]
    assert len(client.get(f"/api/v1/sources/{source_id}/summary").json()["duplicates"]) == 1
    assert _changes(db) == [("delete", COPY, "failed")]


def test_an_unknown_source_is_a_404(client: TestClient) -> None:
    assert _delete(client, 999, "a.png").status_code == 404
