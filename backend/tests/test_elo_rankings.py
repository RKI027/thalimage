"""A collection's ELO ranking: the scored images still in it and not
deleted, from the top, with ties sharing a rank."""

import sqlite3

from fastapi.testclient import TestClient

from tests.helpers import ensure_source, insert_image


def _collection(client: TestClient, name: str, hashes: list[str]) -> int:
    cid = int(client.post("/api/v1/collections", json={"name": name}).json()["id"])
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    return cid


def _vote(client: TestClient, cid: int, winner: str, loser: str) -> None:
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote", json={"winner_hash": winner, "loser_hash": loser}
    )
    assert resp.status_code == 201


def _rankings(client: TestClient, cid: int, **params: object) -> dict:
    resp = client.get(f"/api/v1/collections/{cid}/elo/rankings", params=params)
    assert resp.status_code == 200
    return resp.json()


def _seed(client: TestClient, db: sqlite3.Connection) -> tuple[list[str], int]:
    """h0 beats h1 and h2, h1 beats h2; h3 is never voted on."""
    h = [insert_image(db, f"{0xa10 + i:064x}") for i in range(4)]
    cid = _collection(client, "Alpha", h)
    _vote(client, cid, h[0], h[1])
    _vote(client, cid, h[0], h[2])
    _vote(client, cid, h[1], h[2])
    return h, cid


def _ranked(page: dict) -> list[tuple[str, int]]:
    return [(r["image"]["content_hash"], r["rank"]) for r in page["items"]]


def test_the_ranking_lists_scored_images_from_the_top(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    page = _rankings(client, cid)

    assert _ranked(page) == [(h[0], 1), (h[1], 2), (h[2], 3)]
    assert (page["total"], page["ranked"]) == (3, 3)
    top = page["items"][0]
    assert (top["matches"], top["wins"], top["losses"]) == (2, 2, 0)
    assert top["score"] > 1500


def test_the_ranking_pages(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    page = _rankings(client, cid, offset=1, limit=1)

    assert _ranked(page) == [(h[1], 2)]
    assert page["total"] == 3


def test_equal_scores_share_a_rank(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE elo_scores SET score = 1600 WHERE content_hash IN (?, ?)", (h[0], h[1]))
    db.commit()

    assert [rank for _, rank in _ranked(_rankings(client, cid))] == [1, 1, 3]


def test_images_removed_from_the_collection_are_not_ranked(
    client: TestClient, db: sqlite3.Connection
) -> None:
    h, cid = _seed(client, db)
    client.request("DELETE", f"/api/v1/collections/{cid}/images", json={"hashes": [h[0]]})

    page = _rankings(client, cid)

    assert _ranked(page) == [(h[1], 1), (h[2], 2)]
    assert page["ranked"] == 2


def test_an_image_added_back_regains_its_score(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    client.request("DELETE", f"/api/v1/collections/{cid}/images", json={"hashes": [h[0]]})
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [h[0]]})

    assert _ranked(_rankings(client, cid))[0] == (h[0], 1)


def test_deleted_images_are_not_ranked_and_archived_ones_are(
    client: TestClient, db: sqlite3.Connection
) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (h[1],))
    db.execute("UPDATE images SET archived = 1 WHERE content_hash = ?", (h[0],))
    db.commit()

    page = _rankings(client, cid)

    assert _ranked(page) == [(h[0], 1), (h[2], 2)]
    assert page["items"][0]["image"]["archived"] is True


def test_nsfw_images_are_hidden_but_keep_their_rank(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET nsfw = 1 WHERE content_hash = ?", (h[1],))
    db.commit()

    hidden = _rankings(client, cid)
    shown = _rankings(client, cid, show_nsfw=True)

    assert _ranked(hidden) == [(h[0], 1), (h[2], 3)]
    assert (hidden["total"], hidden["ranked"]) == (2, 3)
    assert _ranked(shown) == [(h[0], 1), (h[1], 2), (h[2], 3)]


def test_a_source_preset_ranks_its_source_s_images(client: TestClient, db: sqlite3.Connection) -> None:
    source_id = ensure_source(db, "/elsewhere")
    h = [insert_image(db, f"{0xb10 + i:064x}", source_id=source_id) for i in range(2)]
    cid = int(db.execute(
        "INSERT INTO collections (name, type, source_id) VALUES ('Preset', 'source_preset', ?)"
        " RETURNING id",
        (source_id,),
    ).fetchone()[0])
    db.commit()
    _vote(client, cid, h[1], h[0])

    assert _ranked(_rankings(client, cid)) == [(h[1], 1), (h[0], 2)]


def test_the_standing_leaves_out_collections_the_image_was_removed_from(
    client: TestClient, db: sqlite3.Connection
) -> None:
    h, cid = _seed(client, db)
    client.request("DELETE", f"/api/v1/collections/{cid}/images", json={"hashes": [h[0]]})

    assert client.get(f"/api/v1/images/{h[0]}/elo").json() == []
    [standing] = client.get(f"/api/v1/images/{h[2]}/elo").json()
    assert (standing["rank"], standing["ranked"]) == (2, 2)
