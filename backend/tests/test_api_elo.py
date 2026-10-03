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


# --- Vote validation (GEN-010, TST-007) ---


def _elo_state(db: sqlite3.Connection) -> tuple[list[tuple], list[tuple]]:
    votes = [tuple(r) for r in db.execute("SELECT * FROM votes ORDER BY id")]
    scores = [tuple(r) for r in db.execute("SELECT * FROM elo_scores ORDER BY 1, 2")]
    return votes, scores


def test_self_vote_is_rejected(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    before = _elo_state(db)
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[0]},
    )
    assert resp.status_code == 400
    assert _elo_state(db) == before


def test_vote_with_unknown_hash_is_rejected(client: TestClient, db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection(client, db)
    before = _elo_state(db)
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": "f" * 64},
    )
    assert resp.status_code == 400
    assert _elo_state(db) == before


def test_vote_for_image_outside_the_collection_is_rejected(
    client: TestClient, db: sqlite3.Connection
) -> None:
    cid, hashes = _seed_collection(client, db)
    client.request(
        "DELETE", f"/api/v1/collections/{cid}/images", json={"hashes": [hashes[4]]}
    )
    before = _elo_state(db)
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[4]},
    )
    assert resp.status_code == 400
    assert _elo_state(db) == before


def test_vote_in_unknown_collection_is_404(client: TestClient, db: sqlite3.Connection) -> None:
    _, hashes = _seed_collection(client, db)
    before = _elo_state(db)
    resp = client.post(
        "/api/v1/collections/999/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
    )
    assert resp.status_code == 404
    assert _elo_state(db) == before


def test_source_preset_pair_and_vote(client: TestClient, db: sqlite3.Connection) -> None:
    """Presets hold no collection_images rows; membership comes from the source."""
    _, hashes = _seed_collection(client, db)
    from thalimage.services.collection_service import get_or_create_source_preset

    preset = get_or_create_source_preset(db, 1, "test").id
    pair = client.get(f"/api/v1/collections/{preset}/elo/pair")
    assert pair.status_code == 200
    assert pair.json()["left"]["content_hash"] in hashes

    resp = client.post(
        f"/api/v1/collections/{preset}/elo/vote",
        json={"winner_hash": hashes[0], "loser_hash": hashes[1]},
    )
    assert resp.status_code == 201


def test_concurrent_votes_match_a_serial_replay(tmp_path) -> None:
    """Votes racing on the same images must not lose updates: the final
    scores equal replaying the recorded votes one after another."""
    import threading

    from thalimage.db.engine import connect, migrate
    from thalimage.services.elo_service import K_FACTOR, record_vote

    path = tmp_path / "race.db"
    setup = connect(path)
    migrate(setup)
    setup.execute("INSERT INTO sources (path) VALUES ('/x')")
    hashes = [c * 64 for c in "abc"]
    for h in hashes:
        setup.execute(
            """INSERT INTO images (content_hash, filename, source_id, relative_path,
                   file_size, width, height, aspect_ratio, format, file_modified,
                   thumb_generated)
               VALUES (?, ?, 1, ?, 1, 1, 1, 1.0, 'PNG', '2024-01-01', 0)""",
            (h, h, h),
        )
    setup.execute("INSERT INTO collections (name) VALUES ('c')")
    setup.executemany(
        "INSERT INTO collection_images (collection_id, content_hash) VALUES (1, ?)",
        [(h,) for h in hashes],
    )
    setup.commit()

    def voter(winner: str, loser: str) -> None:
        conn = connect(path)
        for _ in range(25):
            record_vote(conn, 1, winner_hash=winner, loser_hash=loser)
        conn.close()

    threads = [
        threading.Thread(target=voter, args=(hashes[0], hashes[1])),
        threading.Thread(target=voter, args=(hashes[1], hashes[2])),
        threading.Thread(target=voter, args=(hashes[2], hashes[0])),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = {h: 1500.0 for h in hashes}
    matches = {h: 0 for h in hashes}
    for w, lo in setup.execute("SELECT winner_hash, loser_hash FROM votes ORDER BY id"):
        e_w = 1.0 / (1.0 + 10.0 ** ((expected[lo] - expected[w]) / 400.0))
        expected[w] += K_FACTOR * (1.0 - e_w)
        expected[lo] += K_FACTOR * (0.0 - (1.0 - e_w))
        matches[w] += 1
        matches[lo] += 1

    for h, score, n in setup.execute(
        "SELECT content_hash, score, matches FROM elo_scores WHERE collection_id = 1"
    ):
        assert n == matches[h]
        assert abs(score - expected[h]) < 1e-6
    setup.close()
