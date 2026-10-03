"""Deleting a source or a collection removes exactly its own data (GEN-003, TST-001)."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image


from tests.helpers import scan_source


def _preset_id(client: TestClient, source_id: int) -> int:
    presets = client.get("/api/v1/collections", params={"type": "source_preset"}).json()
    return next(c["id"] for c in presets if c["source_id"] == source_id)


def _vote(client: TestClient, collection_id: int, winner: str, loser: str) -> None:
    resp = client.post(
        f"/api/v1/collections/{collection_id}/elo/vote",
        json={"winner_hash": winner, "loser_hash": loser},
    )
    assert resp.status_code == 201, resp.text


def _count(db: sqlite3.Connection, sql: str, *params: object) -> int:
    return int(db.execute(sql, params).fetchone()[0])


def test_delete_collection_with_votes(client: TestClient, image_dir: Path) -> None:
    _, hashes = scan_source(client, image_dir)
    coll = client.post("/api/v1/collections", json={"name": "ranked"}).json()["id"]
    client.post(f"/api/v1/collections/{coll}/images", json={"hashes": hashes})
    _vote(client, coll, hashes[0], hashes[1])

    assert client.delete(f"/api/v1/collections/{coll}").status_code == 204
    assert client.get(f"/api/v1/collections/{coll}").status_code == 404


def test_delete_collection_removes_only_its_elo_rows(
    client: TestClient, db: sqlite3.Connection, image_dir: Path
) -> None:
    _, hashes = scan_source(client, image_dir)
    gone = client.post("/api/v1/collections", json={"name": "gone"}).json()["id"]
    kept = client.post("/api/v1/collections", json={"name": "kept"}).json()["id"]
    for c in (gone, kept):
        client.post(f"/api/v1/collections/{c}/images", json={"hashes": hashes})
        _vote(client, c, hashes[0], hashes[1])

    client.delete(f"/api/v1/collections/{gone}")

    for table in ("votes", "elo_scores"):
        assert _count(db, f"SELECT COUNT(*) FROM {table} WHERE collection_id = ?", gone) == 0
        assert _count(db, f"SELECT COUNT(*) FROM {table} WHERE collection_id = ?", kept) > 0


def test_delete_collection_reparents_its_children(
    client: TestClient, db: sqlite3.Connection
) -> None:
    parent = client.post("/api/v1/collections", json={"name": "p"}).json()["id"]
    child = client.post(
        "/api/v1/collections", json={"name": "c", "parent_id": parent}
    ).json()["id"]

    assert client.delete(f"/api/v1/collections/{parent}").status_code == 204
    assert client.get(f"/api/v1/collections/{child}").json()["parent_id"] is None


def test_delete_source_removes_its_data_and_nothing_else(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    for i, color in enumerate(("red", "green")):
        Image.new("RGB", (10 + i, 10), color).save(dir_a / f"a{i}.png")
    for i, color in enumerate(("blue", "yellow", "purple")):
        Image.new("RGB", (10 + i, 12), color).save(dir_b / f"b{i}.png")
    src_a, a = scan_source(client, dir_a)
    src_b, b = scan_source(client, dir_b)
    preset_a, preset_b = _preset_id(client, src_a), _preset_id(client, src_b)

    # A manual collection spanning both sources, with votes inside each
    # source and across them; votes on both presets; tags on both sides.
    manual = client.post("/api/v1/collections", json={"name": "mixed"}).json()["id"]
    client.post(f"/api/v1/collections/{manual}/images", json={"hashes": a + b})
    _vote(client, manual, a[0], a[1])
    _vote(client, manual, b[0], b[1])
    _vote(client, manual, a[0], b[2])
    _vote(client, preset_a, a[0], a[1])
    _vote(client, preset_b, b[1], b[2])
    tag = client.post("/api/v1/tags", json={"name": "keep"}).json()["id"]
    for h in (a[0], b[0]):
        client.post(f"/api/v1/images/{h}/tags", json={"tag_id": tag})

    assert client.delete(f"/api/v1/sources/{src_a}").status_code == 204

    in_a = ",".join("?" * len(a))
    # Nothing of source A remains...
    assert _count(db, "SELECT COUNT(*) FROM sources WHERE id = ?", src_a) == 0
    assert _count(db, "SELECT COUNT(*) FROM collections WHERE id = ?", preset_a) == 0
    for table, col in (
        ("images", "content_hash"),
        ("image_metadata", "content_hash"),
        ("collection_images", "content_hash"),
        ("elo_scores", "content_hash"),
        ("image_tags", "image_hash"),
        ("votes", "winner_hash"),
        ("votes", "loser_hash"),
    ):
        assert _count(db, f"SELECT COUNT(*) FROM {table} WHERE {col} IN ({in_a})", *a) == 0, table
    for table in ("votes", "elo_scores"):
        assert _count(db, f"SELECT COUNT(*) FROM {table} WHERE collection_id = ?", preset_a) == 0

    # ...and everything of source B does.
    in_b = ",".join("?" * len(b))
    assert _count(db, f"SELECT COUNT(*) FROM images WHERE content_hash IN ({in_b})", *b) == 3
    assert _count(db, f"SELECT COUNT(*) FROM image_metadata WHERE content_hash IN ({in_b})", *b) == 3
    assert _count(db, "SELECT COUNT(*) FROM collection_images WHERE collection_id = ?", manual) == 3
    assert _count(db, "SELECT COUNT(*) FROM votes WHERE collection_id = ?", manual) == 1
    assert _count(db, "SELECT COUNT(*) FROM votes WHERE collection_id = ?", preset_b) == 1
    assert _count(db, "SELECT COUNT(*) FROM elo_scores WHERE collection_id = ?", preset_b) == 2
    assert _count(db, "SELECT COUNT(*) FROM image_tags WHERE image_hash = ?", b[0]) == 1
    assert _count(db, "SELECT COUNT(*) FROM tags WHERE id = ?", tag) == 1
    assert _count(db, "SELECT COUNT(*) FROM collections WHERE id IN (?, ?)", manual, preset_b) == 2
