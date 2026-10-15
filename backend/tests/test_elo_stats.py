"""Voting statistics for a collection: every image voting can draw with its
matches and standing, how pairs have met, and the top's head-to-heads."""

import sqlite3

from fastapi.testclient import TestClient

from tests.helpers import ensure_source, insert_image


def _collection(client: TestClient, hashes: list[str]) -> int:
    cid = int(client.post("/api/v1/collections", json={"name": "Alpha"}).json()["id"])
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    return cid


def _vote(client: TestClient, cid: int, winner: str, loser: str) -> None:
    resp = client.post(
        f"/api/v1/collections/{cid}/elo/vote", json={"winner_hash": winner, "loser_hash": loser}
    )
    assert resp.status_code == 201


def _stats(client: TestClient, cid: int, **params: object) -> dict:
    resp = client.get(f"/api/v1/collections/{cid}/elo/stats", params=params)
    assert resp.status_code == 200
    return resp.json()


def _seed(client: TestClient, db: sqlite3.Connection) -> tuple[list[str], int]:
    """h0 beats h1 twice and h2 once, h1 beats h2; h3 is never voted on."""
    h = [insert_image(db, f"{0xc10 + i:064x}") for i in range(4)]
    cid = _collection(client, h)
    _vote(client, cid, h[0], h[1])
    _vote(client, cid, h[0], h[1])
    _vote(client, cid, h[0], h[2])
    _vote(client, cid, h[1], h[2])
    return h, cid


def test_every_image_voting_can_draw_with_its_matches(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    images = {i["content_hash"]: i for i in _stats(client, cid)["images"]}

    assert {k: (v["matches"], v["rank"]) for k, v in images.items()} == {
        h[0]: (3, 1), h[1]: (3, 2), h[2]: (2, 3), h[3]: (0, None)
    }
    assert images[h[0]]["score"] > 1500
    assert images[h[3]]["score"] is None



def test_marks_the_images_hidden_while_nsfw_is_hidden(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET nsfw = 1 WHERE content_hash = ?", (h[0],))
    db.commit()
    other = int(client.post("/api/v1/collections", json={"name": "Spicy"}).json()["id"])
    client.post(f"/api/v1/collections/{other}/images", json={"hashes": [h[1]]})
    db.execute("UPDATE collections SET nsfw = 1 WHERE id = ?", (other,))
    db.commit()

    stats = _stats(client, cid)

    assert {i["content_hash"]: i["nsfw"] for i in stats["images"]} == {
        h[0]: True, h[1]: True, h[2]: False, h[3]: False
    }
    assert [i["nsfw"] for i in stats["top"]] == [True, True, False]

def test_archived_deleted_and_removed_images_are_left_out(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET archived = 1 WHERE content_hash = ?", (h[0],))
    db.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (h[3],))
    db.commit()
    client.request("DELETE", f"/api/v1/collections/{cid}/images", json={"hashes": [h[2]]})

    stats = _stats(client, cid)

    assert [(i["content_hash"], i["rank"]) for i in stats["images"]] == [(h[1], 2)]


def test_how_pairs_have_met(client: TestClient, db: sqlite3.Connection) -> None:
    _, cid = _seed(client, db)

    assert _stats(client, cid)["pairs"] == {"met": 3, "possible": 6, "repeated": 1, "most_meetings": 2}


def test_pairs_count_only_meetings_between_covered_images(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET archived = 1 WHERE content_hash = ?", (h[2],))
    db.commit()

    assert _stats(client, cid)["pairs"] == {"met": 1, "possible": 3, "repeated": 1, "most_meetings": 2}


def test_the_top_s_head_to_heads(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    stats = _stats(client, cid, top=2)

    assert [t["content_hash"] for t in stats["top"]] == [h[0], h[1]]
    assert stats["head_to_head"] == [{"winner": h[0], "loser": h[1], "count": 2}]


def test_a_source_preset_covers_its_source_s_images(client: TestClient, db: sqlite3.Connection) -> None:
    source_id = ensure_source(db, "/elsewhere")
    h = [insert_image(db, f"{0xd10 + i:064x}", source_id=source_id) for i in range(3)]
    cid = int(db.execute(
        "INSERT INTO collections (name, type, source_id) VALUES ('Preset', 'source_preset', ?)"
        " RETURNING id",
        (source_id,),
    ).fetchone()[0])
    db.commit()
    _vote(client, cid, h[1], h[0])

    stats = _stats(client, cid)

    assert len(stats["images"]) == 3
    assert stats["pairs"]["met"] == 1


def test_an_unknown_collection_has_no_stats(client: TestClient) -> None:
    assert client.get("/api/v1/collections/999/elo/stats").status_code == 404
