"""Filtering a collection to the top or bottom part of its ELO ranking: a
percentage of the whole ranking, rounded up, intersected with the other
filters; images never voted on never pass."""

import sqlite3

from fastapi.testclient import TestClient

from tests.helpers import ensure_source, insert_image


def _seed(client: TestClient, db: sqlite3.Connection, *, source_id: int | None = None) -> tuple[list[str], int]:
    """Five images scored 1540, 1530, 1520, 1510 down to h3, and h4 never voted on."""
    h = [insert_image(db, f"{0xf10 + i:064x}", source_id=source_id) for i in range(5)]
    if source_id is None:
        cid = int(client.post("/api/v1/collections", json={"name": "Alpha"}).json()["id"])
        client.post(f"/api/v1/collections/{cid}/images", json={"hashes": h})
    else:
        cid = int(db.execute(
            "INSERT INTO collections (name, type, source_id) VALUES ('Preset', 'source_preset', ?)"
            " RETURNING id",
            (source_id,),
        ).fetchone()[0])
    for i in range(4):
        db.execute(
            "INSERT INTO elo_scores (content_hash, collection_id, score, matches) VALUES (?, ?, ?, 1)",
            (h[i], cid, 1540 - 10 * i),
        )
    db.commit()
    return h, cid


def _listed(client: TestClient, cid: int, **params: object) -> tuple[set[str], int]:
    resp = client.get("/api/v1/images", params={"collection_id": cid, **params})
    assert resp.status_code == 200
    page = resp.json()
    return {i["content_hash"] for i in page["items"]}, page["total_count"]


def test_the_top_part_of_the_ranking(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    assert _listed(client, cid, elo_end="top", elo_percent=50) == ({h[0], h[1]}, 2)


def test_the_bottom_part_of_the_ranking(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    assert _listed(client, cid, elo_end="bottom", elo_percent=25) == ({h[3]}, 1)


def test_the_share_is_rounded_up(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    assert _listed(client, cid, elo_end="top", elo_percent=1) == ({h[0]}, 1)
    assert _listed(client, cid, elo_end="top", elo_percent=51)[1] == 3


def test_images_never_voted_on_never_pass(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    assert _listed(client, cid, elo_end="bottom", elo_percent=100) == (set(h[:4]), 4)


def test_the_share_is_of_the_whole_ranking(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE images SET aspect_ratio = 0.5 WHERE content_hash IN (?, ?)", (h[1], h[2]))
    db.commit()

    top_half_portraits = _listed(client, cid, elo_end="top", elo_percent=50, aspect_ratio_filter="portrait")

    assert top_half_portraits == ({h[1]}, 1)


def test_ties_at_the_edge_follow_the_elo_sort(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)
    db.execute("UPDATE elo_scores SET score = 1600 WHERE collection_id = ?", (cid,))
    db.commit()
    by_elo = client.get(
        "/api/v1/images", params={"collection_id": cid, "sort": "elo", "dir": "desc"}
    ).json()["items"]

    top, _ = _listed(client, cid, elo_end="top", elo_percent=50)

    assert top == {i["content_hash"] for i in by_elo[:2]}


def test_a_source_preset_filters_by_its_own_ranking(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db, source_id=ensure_source(db, "/elsewhere"))

    assert _listed(client, cid, elo_end="top", elo_percent=25) == ({h[0]}, 1)


def test_the_viewer_walks_the_filtered_listing(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    resp = client.get(
        f"/api/v1/images/{h[0]}/neighbors",
        params={"collection_id": cid, "sort": "elo", "dir": "desc", "elo_end": "top", "elo_percent": 50},
    )

    assert [i["content_hash"] for i in resp.json()["after"]] == [h[1]]


def test_voting_draws_from_the_filtered_part(client: TestClient, db: sqlite3.Connection) -> None:
    h, cid = _seed(client, db)

    for _ in range(5):
        pair = client.get(
            f"/api/v1/collections/{cid}/elo/pair", params={"elo_end": "bottom", "elo_percent": 50}
        ).json()
        assert {pair["left"]["content_hash"], pair["right"]["content_hash"]} == {h[2], h[3]}


def test_the_percentage_must_be_between_1_and_100(client: TestClient, db: sqlite3.Connection) -> None:
    _, cid = _seed(client, db)

    for percent in (0, 101):
        resp = client.get("/api/v1/images", params={"collection_id": cid, "elo_end": "top", "elo_percent": percent})
        assert resp.status_code == 422
