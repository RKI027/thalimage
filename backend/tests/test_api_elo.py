"""Tests for ELO voting API endpoints."""

import sqlite3

from fastapi.testclient import TestClient


def _seed_collection(client: TestClient, db: sqlite3.Connection) -> tuple[int, list[str]]:
    """Create a collection with images directly in DB (no async scan needed)."""
    db.execute(
        "INSERT INTO sources (path, label, recursive) VALUES (?, ?, ?)",
        ("/test", "test", True),
    )

    hashes = []
    for i in range(5):
        h = f"elohash_{i:04d}"
        db.execute(
            """INSERT INTO images
               (content_hash, filename, source_id, relative_path,
                file_size, width, height, aspect_ratio, format,
                file_modified, thumb_generated)
               VALUES (?, ?, 1, ?, 1000, 100, 100, 1.0, 'PNG', '2024-01-01T00:00:00', 1)
            """,
            (h, f"img_{i}.png", f"img_{i}.png"),
        )
        hashes.append(h)
    db.commit()

    resp = client.post("/api/v1/collections", json={"name": "ELO Test"})
    cid = resp.json()["id"]

    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    return cid, hashes


def test_get_pair(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    resp = client.get(f"/api/v1/collections/{cid}/elo/pair")
    assert resp.status_code == 200
    data = resp.json()
    assert data["left"]["content_hash"] in hashes
    assert data["right"]["content_hash"] in hashes
    assert data["left"]["content_hash"] != data["right"]["content_hash"]


def test_get_pair_too_few_images(client: TestClient, db: sqlite3.Connection) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Empty"})
    cid = resp.json()["id"]
    resp = client.get(f"/api/v1/collections/{cid}/elo/pair")
    assert resp.status_code == 400


def test_vote(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "recorded"


def test_rankings(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
    )
    resp = client.get(f"/api/v1/collections/{cid}/elo/rankings")
    assert resp.status_code == 200
    rankings = resp.json()
    assert len(rankings) == 2
    assert rankings[0]["content_hash"] == hashes[0]
    assert rankings[0]["score"] > rankings[1]["score"]


def test_rankings_empty(client: TestClient, db: sqlite3.Connection) -> None:
    cid, _ = _seed_collection(client, db)
    resp = client.get(f"/api/v1/collections/{cid}/elo/rankings")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sort_by_elo_orders_by_score(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    # hashes[0] wins repeatedly over hashes[1]; the rest keep the 1500 default.
    for _ in range(3):
        client.post(
            f"/api/v1/collections/{cid}/elo/vote",
            json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
        )

    data = client.get(
        "/api/v1/images", params={"collection_id": cid, "sort": "elo", "dir": "desc"}
    ).json()
    ordered = [i["content_hash"] for i in data["items"]]
    assert ordered[0] == hashes[0]   # highest score first
    assert ordered[-1] == hashes[1]  # lowest score last


def test_sort_by_elo_pagination_covers_all(
    client: TestClient, db: sqlite3.Connection
) -> None:
    cid, hashes = _seed_collection(client, db)
    client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
    )

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params = {"collection_id": cid, "sort": "elo", "dir": "desc", "limit": 2}
        if cursor:
            params["cursor"] = cursor
        data = client.get("/api/v1/images", params=params).json()
        seen.extend(i["content_hash"] for i in data["items"])
        cursor = data["next_cursor"]
        if cursor is None:
            break

    assert sorted(seen) == sorted(hashes)
    assert len(seen) == len(set(seen))
