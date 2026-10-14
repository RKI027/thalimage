"""Deleting an image from disk: every copy in every source goes, only when
all those sources are writable. The image is then marked deleted, keeping
its tags, scores, votes and collections, so a copy found again by a later
scan brings it back with its history."""

import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers import scan_source

COPY = str(Path("sub") / "a-copy.png")


@pytest.fixture
def two_sources(client: TestClient, image_dir: Path, tmp_path: Path) -> tuple[int, int, str]:
    """a.png has a copy in its own source (sub/a-copy.png) and one in a
    second source (other/a.png); both sources are writable."""
    shutil.copy(image_dir / "a.png", image_dir / COPY)
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy(image_dir / "a.png", other / "a.png")
    first, hashes = scan_source(client, image_dir)
    second, _ = scan_source(client, other)
    for source_id in (first, second):
        client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    return first, second, hashes[0]


def _copies(client: TestClient, content_hash: str) -> list[dict]:
    resp = client.get(f"/api/v1/images/{content_hash}/copies")
    assert resp.status_code == 200
    return resp.json()


def _delete(client: TestClient, content_hash: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/images/{content_hash}/delete")


def test_the_copies_of_an_image_are_listed_with_their_sources(
    client: TestClient, image_dir: Path, tmp_path: Path, two_sources: tuple[int, int, str]
) -> None:
    first, second, content_hash = two_sources

    assert _copies(client, content_hash) == [
        {"source_id": first, "source_path": str(image_dir), "relative_path": "a.png",
         "writable": True},
        {"source_id": first, "source_path": str(image_dir), "relative_path": COPY,
         "writable": True},
        {"source_id": second, "source_path": str(tmp_path / "other"), "relative_path": "a.png",
         "writable": True},
    ]


def test_the_copies_of_an_unknown_image_are_a_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/images/{'0' * 64}/copies").status_code == 404


def test_deleting_an_image_removes_every_copy_and_hides_it(
    client: TestClient,
    db: sqlite3.Connection,
    image_dir: Path,
    tmp_path: Path,
    two_sources: tuple[int, int, str],
) -> None:
    first, second, content_hash = two_sources

    resp = _delete(client, content_hash)

    assert resp.status_code == 200
    assert resp.json() == {"deleted": 3, "failed": []}
    assert not (image_dir / "a.png").exists()
    assert not (image_dir / COPY).exists()
    assert not (tmp_path / "other" / "a.png").exists()
    assert client.get(f"/api/v1/images/{content_hash}").status_code == 404
    listed = [i["content_hash"] for i in client.get("/api/v1/images").json()["items"]]
    assert content_hash not in listed
    changes = db.execute(
        "SELECT source_id, operation, path, outcome FROM file_changes ORDER BY id"
    ).fetchall()
    assert [tuple(r) for r in changes] == [
        (first, "delete", "a.png", "done"),
        (first, "delete", COPY, "done"),
        (second, "delete", "a.png", "done"),
    ]


def test_a_deleted_image_keeps_its_history_and_returns_when_found_again(
    client: TestClient, image_dir: Path, two_sources: tuple[int, int, str]
) -> None:
    first, _, content_hash = two_sources
    tag = client.post("/api/v1/tags", json={"name": "keep"}).json()
    client.post(f"/api/v1/images/{content_hash}/tags", json={"tag_id": tag["id"]})
    kept = image_dir.parent / "kept.png"
    shutil.copy(image_dir / "a.png", kept)

    _delete(client, content_hash)
    shutil.copy(kept, image_dir / "a.png")
    client.post(f"/api/v1/sources/{first}/scan")
    client.get(f"/api/v1/sources/{first}/scan/status")

    assert client.get(f"/api/v1/images/{content_hash}").status_code == 200
    tags = client.get(f"/api/v1/images/{content_hash}/tags").json()
    assert [t["name"] for t in tags] == ["keep"]


def test_a_copy_in_a_read_only_source_refuses_the_whole_delete(
    client: TestClient, image_dir: Path, tmp_path: Path, two_sources: tuple[int, int, str]
) -> None:
    _, second, content_hash = two_sources
    client.patch(f"/api/v1/sources/{second}", json={"writable": False})

    resp = _delete(client, content_hash)

    assert resp.status_code == 409
    assert "not marked writable" in resp.json()["detail"]
    assert (image_dir / "a.png").exists() and (image_dir / COPY).exists()
    assert (tmp_path / "other" / "a.png").exists()


def test_a_copy_changed_since_the_scan_refuses_the_whole_delete(
    client: TestClient, image_dir: Path, tmp_path: Path, two_sources: tuple[int, int, str]
) -> None:
    _, _, content_hash = two_sources
    (tmp_path / "other" / "a.png").write_bytes(b"something else")

    resp = _delete(client, content_hash)

    assert resp.status_code == 409
    assert "rescan" in resp.json()["detail"]
    assert (image_dir / "a.png").exists() and (image_dir / COPY).exists()


def test_a_failed_removal_keeps_the_image(
    client: TestClient,
    image_dir: Path,
    two_sources: tuple[int, int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, content_hash = two_sources
    real_remove = os.remove

    def refuse_first(path: object) -> None:
        if Path(str(path)) == image_dir / "a.png":
            raise PermissionError(13, "Permission denied", str(path))
        real_remove(path)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "remove", refuse_first)
    resp = _delete(client, content_hash)

    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] == 2
    [failure] = body["failed"]
    assert failure["relative_path"] == "a.png" and "Permission denied" in failure["error"]
    image = client.get(f"/api/v1/images/{content_hash}").json()
    assert image["relative_path"] == "a.png"


def test_deleting_an_unknown_image_is_a_404(client: TestClient) -> None:
    assert _delete(client, "0" * 64).status_code == 404
