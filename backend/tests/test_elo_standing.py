"""An image's ELO standing in each collection it has been voted in: score,
rank among the collection's scored images, matches, wins and losses."""

import sqlite3

from fastapi.testclient import TestClient

from tests.helpers import insert_image


def _collection(client: TestClient, name: str, hashes: list[str]) -> int:
    cid = int(client.post("/api/v1/collections", json={"name": name}).json()["id"])
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    return cid


def _vote(client: TestClient, cid: int, winner: str, loser: str) -> None:
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote", json={"winner_hash": winner, "loser_hash": loser}
    )
    assert resp.status_code == 201


def _standing(client: TestClient, content_hash: str) -> list[dict]:
    resp = client.get(f"/api/v1/images/{content_hash}/elo")
    assert resp.status_code == 200
    return resp.json()


def _seed(client: TestClient, db: sqlite3.Connection) -> tuple[list[str], int, int]:
    """h0 beats h1 and h2, h1 beats h2 in "Alpha"; h2 beats h0 in "Beta"."""
    h = [insert_image(db, f"{0xe10 + i:064x}") for i in range(4)]
    alpha = _collection(client, "Alpha", h)
    beta = _collection(client, "Beta", h)
    _vote(client, alpha, h[0], h[1])
    _vote(client, alpha, h[0], h[2])
    _vote(client, alpha, h[1], h[2])
    _vote(client, beta, h[2], h[0])
    return h, alpha, beta


def test_an_image_s_standing_in_each_collection(client: TestClient, db: sqlite3.Connection) -> None:
    h, alpha, beta = _seed(client, db)

    standing = _standing(client, h[0])

    assert [
        {k: s[k] for k in ("collection_id", "collection_name", "rank", "ranked", "matches", "wins", "losses")}
        for s in standing
    ] == [
        {"collection_id": alpha, "collection_name": "Alpha", "rank": 1, "ranked": 3,
         "matches": 2, "wins": 2, "losses": 0},
        {"collection_id": beta, "collection_name": "Beta", "rank": 2, "ranked": 2,
         "matches": 1, "wins": 0, "losses": 1},
    ]
    assert standing[0]["score"] > 1500 > standing[1]["score"]


def test_an_image_never_voted_on_has_no_standing(client: TestClient, db: sqlite3.Connection) -> None:
    h, _, _ = _seed(client, db)
    assert _standing(client, h[3]) == []


def test_deleted_images_do_not_count_in_the_rank(client: TestClient, db: sqlite3.Connection) -> None:
    h, alpha, _ = _seed(client, db)
    db.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (h[1],))
    db.commit()

    [in_alpha, _] = _standing(client, h[2])

    assert (in_alpha["collection_id"], in_alpha["rank"], in_alpha["ranked"]) == (alpha, 2, 2)


def test_equal_scores_share_a_rank(client: TestClient, db: sqlite3.Connection) -> None:
    h, alpha, _ = _seed(client, db)
    db.execute("UPDATE elo_scores SET score = 1600 WHERE collection_id = ?", (alpha,))
    db.commit()

    assert [s["rank"] for s in _standing(client, h[1]) if s["collection_id"] == alpha] == [1]


def test_the_standing_of_an_unknown_image_is_a_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/images/{'0' * 64}/elo").status_code == 404
