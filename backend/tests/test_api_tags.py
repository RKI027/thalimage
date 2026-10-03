"""Tests for the /tags and /images/{hash}/tags endpoints (TST-005)."""

import sqlite3

from fastapi.testclient import TestClient

UNKNOWN = "f" * 64


def _image(db: sqlite3.Connection, h: str = "a" * 64) -> str:
    if db.execute("SELECT 1 FROM sources WHERE id = 1").fetchone() is None:
        db.execute("INSERT INTO sources (id, path) VALUES (1, '/x')")
    db.execute(
        """INSERT INTO images (content_hash, filename, source_id, relative_path,
               file_size, width, height, aspect_ratio, format, file_modified,
               thumb_generated)
           VALUES (?, 'x.png', 1, ?, 1, 1, 1, 1.0, 'PNG', '2024-01-01', 0)""",
        (h, h),
    )
    db.commit()
    return h


def _tag(client: TestClient, name: str) -> int:
    resp = client.post("/api/v1/tags", json={"name": name})
    assert resp.status_code == 201
    return int(resp.json()["id"])


def test_create_and_list(client: TestClient) -> None:
    _tag(client, "beta")
    _tag(client, "alpha")
    names = [t["name"] for t in client.get("/api/v1/tags").json()]
    assert names == ["alpha", "beta"]


def test_search(client: TestClient) -> None:
    _tag(client, "landscape")
    _tag(client, "portrait")
    names = [t["name"] for t in client.get("/api/v1/tags", params={"search": "LAND"}).json()]
    assert names == ["landscape"]


def test_create_duplicate_is_409(client: TestClient) -> None:
    _tag(client, "dup")
    assert client.post("/api/v1/tags", json={"name": "dup"}).status_code == 409


def test_rename(client: TestClient) -> None:
    tid = _tag(client, "old")
    resp = client.patch(f"/api/v1/tags/{tid}", json={"name": "new"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "new"


def test_rename_to_existing_name_is_409(client: TestClient) -> None:
    _tag(client, "taken")
    tid = _tag(client, "free")
    assert client.patch(f"/api/v1/tags/{tid}", json={"name": "taken"}).status_code == 409
    assert client.get("/api/v1/tags", params={"search": "free"}).json()[0]["id"] == tid


def test_patch_unknown_is_404(client: TestClient) -> None:
    assert client.patch("/api/v1/tags/999", json={"name": "x"}).status_code == 404


def test_delete(client: TestClient) -> None:
    tid = _tag(client, "gone")
    assert client.delete(f"/api/v1/tags/{tid}").status_code == 204
    assert client.delete(f"/api/v1/tags/{tid}").status_code == 404


def test_tag_and_untag_image(client: TestClient, db: sqlite3.Connection) -> None:
    h = _image(db)
    tid = _tag(client, "red")
    assert client.post(f"/api/v1/images/{h}/tags", json={"tag_id": tid}).status_code == 204
    # Tagging twice is idempotent.
    assert client.post(f"/api/v1/images/{h}/tags", json={"tag_id": tid}).status_code == 204
    assert [t["name"] for t in client.get(f"/api/v1/images/{h}/tags").json()] == ["red"]

    assert client.delete(f"/api/v1/images/{h}/tags/{tid}").status_code == 204
    assert client.get(f"/api/v1/images/{h}/tags").json() == []
    assert client.delete(f"/api/v1/images/{h}/tags/{tid}").status_code == 404


def test_tag_unknown_image_is_404(client: TestClient) -> None:
    tid = _tag(client, "red")
    resp = client.post(f"/api/v1/images/{UNKNOWN}/tags", json={"tag_id": tid})
    assert resp.status_code == 404


def test_tag_image_with_unknown_tag_is_404(client: TestClient, db: sqlite3.Connection) -> None:
    h = _image(db)
    assert client.post(f"/api/v1/images/{h}/tags", json={"tag_id": 999}).status_code == 404


def test_malformed_hash_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/images/not-a-hash/tags").status_code == 422
