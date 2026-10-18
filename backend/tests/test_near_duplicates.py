"""Near-duplicate groups, through the image listing."""

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from thalimage.services.near_duplicates import keep_on_disk
from tests.helpers import ensure_source, insert_image


def _image(db: sqlite3.Connection, name: str, picture: int, *, source: str = "/test") -> str:
    """An image keyed by `name` repeated, whose perceptual hash has the bits
    of `picture`."""
    key = name * 64
    insert_image(db, key, source_id=ensure_source(db, source))
    signed = picture - (1 << 64) if picture >= 1 << 63 else picture
    db.execute("UPDATE images SET perceptual_hash = ? WHERE content_hash = ?", (signed, key))
    db.commit()
    return key


def _bits(*positions: int) -> int:
    return sum(1 << p for p in positions)


def _listed(client: TestClient, **params: object) -> list[str]:
    params.setdefault("near_duplicates", 0.15)
    resp = client.get("/api/v1/images", params=params)
    assert resp.status_code == 200, resp.text
    return [i["content_hash"][0] for i in resp.json()["items"]]


def test_only_images_that_look_like_another_are_listed(
    client: TestClient, db: sqlite3.Connection
) -> None:
    _image(db, "a", 0)
    _image(db, "b", _bits(1, 2, 3))
    _image(db, "c", _bits(*range(0, 64, 2)))

    assert _listed(client) == ["a", "b"]


def test_a_group_gathers_what_is_close_to_its_first_image(
    client: TestClient, db: sqlite3.Connection
) -> None:
    # b lies within 8 bits of a and of c, which are 16 bits apart.
    _image(db, "a", 0)
    _image(db, "b", _bits(*range(8)))
    _image(db, "c", _bits(*range(16)))

    assert _listed(client) == ["a", "b"]
    assert _listed(client, dir="desc") == ["c", "b"]


def test_groups_follow_one_another_in_the_listing_order(
    client: TestClient, db: sqlite3.Connection
) -> None:
    far = _bits(*range(0, 64, 2))
    _image(db, "a", 0)
    _image(db, "b", far)
    _image(db, "c", far | 1)
    _image(db, "d", 1)

    resp = client.get("/api/v1/images", params={"near_duplicates": 0.15}).json()

    assert [(i["content_hash"][0], i["duplicate_group"]) for i in resp["items"]] == [
        ("a", 0), ("d", 0), ("b", 1), ("c", 1),
    ]
    assert resp["total_count"] == 4


def test_the_threshold_decides_what_looks_alike(
    client: TestClient, db: sqlite3.Connection
) -> None:
    _image(db, "a", 0)
    _image(db, "b", _bits(*range(8)))

    assert _listed(client, near_duplicates=0.05) == []
    assert _listed(client, near_duplicates=0.15) == ["a", "b"]


def test_the_threshold_rounds_to_the_nearest_bit(
    client: TestClient, db: sqlite3.Connection
) -> None:
    # 0.15 of 64 bits is 9.6: a pair 10 bits apart is within it.
    _image(db, "a", 0)
    _image(db, "b", _bits(*range(10)))

    assert _listed(client, near_duplicates=0.15) == ["a", "b"]


def test_a_threshold_past_the_widest_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/images", params={"near_duplicates": 0.31}).status_code == 422


def test_the_other_filters_choose_what_is_compared(
    client: TestClient, db: sqlite3.Connection
) -> None:
    _image(db, "a", 0, source="/one")
    _image(db, "b", 1, source="/one")
    _image(db, "c", 3, source="/two")
    one = ensure_source(db, "/one")
    two = ensure_source(db, "/two")

    assert _listed(client, source_id=one) == ["a", "b"]
    assert _listed(client, source_id=two) == []


def test_an_image_scanned_since_joins_its_group(
    client: TestClient, db: sqlite3.Connection
) -> None:
    _image(db, "a", 0)
    _image(db, "b", 1)
    assert _listed(client) == ["a", "b"]

    _image(db, "c", 3)

    assert _listed(client) == ["a", "b", "c"]


def test_pages_walk_the_groups(client: TestClient, db: sqlite3.Connection) -> None:
    for key, picture in (("a", 0), ("b", 1), ("c", 3)):
        _image(db, key, picture)

    seen: list[str] = []
    cursor = None
    while True:
        params: dict[str, object] = {"near_duplicates": 0.15, "limit": 1, "dir": "desc"}
        if cursor:
            params["cursor"] = cursor
        page = client.get("/api/v1/images", params=params).json()
        seen += [i["content_hash"][0] for i in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert seen == ["c", "b", "a"]


def test_the_viewer_steps_through_the_groups(client: TestClient, db: sqlite3.Connection) -> None:
    far = _bits(*range(0, 64, 2))
    for key, picture in (("a", 0), ("b", far), ("c", far | 1), ("d", 1)):
        _image(db, key, picture)
    params = {"near_duplicates": 0.15}

    around = client.get(f"/api/v1/images/{'d' * 64}/neighbors", params=params).json()
    walk = client.get("/api/v1/images/sequence", params=params).json()

    assert [i["content_hash"][0] for i in around["before"]] == ["a"]
    assert [i["content_hash"][0] for i in around["after"]] == ["b", "c"]
    assert around["position"] == 1
    assert [i["content_hash"][0] for i in walk] == ["a", "d", "b", "c"]
    assert around["duplicate_group"] == 0


def _delete(db: sqlite3.Connection, name: str) -> None:
    db.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (name * 64,))
    db.commit()


def test_a_deleted_image_leaves_its_group(client: TestClient, db: sqlite3.Connection) -> None:
    far = _bits(*range(0, 64, 2))
    for key, picture in (("a", 0), ("b", 1), ("c", far), ("d", far | 1)):
        _image(db, key, picture)
    assert _listed(client) == ["a", "b", "c", "d"]

    _delete(db, "a")

    assert _listed(client) == ["c", "d"]


def test_an_image_whose_picture_changed_regroups(
    client: TestClient, db: sqlite3.Connection
) -> None:
    far = _bits(*range(0, 64, 2))
    _image(db, "a", 0)
    _image(db, "b", 1)
    _image(db, "c", far)
    assert _listed(client) == ["a", "b"]

    db.execute("UPDATE images SET perceptual_hash = ? WHERE content_hash = ?", (far | 1, "b" * 64))
    db.commit()

    assert _listed(client) == ["b", "c"]


def test_an_image_left_out_of_the_groups_keeps_its_place_among_them(
    client: TestClient, db: sqlite3.Connection
) -> None:
    far = _bits(*range(0, 64, 2))
    other = _bits(*range(1, 64, 2))
    for key, picture in (("a", 0), ("b", 1), ("c", far), ("d", far | 1), ("e", other), ("f", other | 1)):
        _image(db, key, picture)
    _delete(db, "c")

    around = client.get(f"/api/v1/images/{'d' * 64}/neighbors", params={"near_duplicates": 0.15}).json()

    assert [i["content_hash"][0] for i in around["before"]] == ["a", "b"]
    assert [i["content_hash"][0] for i in around["after"]] == ["e", "f"]
    assert around["position"] == 2
    assert around["duplicate_group"] is None


def _kept(tmp_path: Path) -> Path:
    """Where the app started by the `client` fixture keeps the pairs."""
    return tmp_path / "data" / "cache" / "near-duplicates.json"


def test_a_restart_starts_from_the_pairs_kept_on_disk(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    _image(db, "a", 0)
    _image(db, "b", 1)
    assert _listed(client) == ["a", "b"]
    kept = json.loads(_kept(tmp_path).read_text())

    # Pairs removed from the file can only be missing after a restart if
    # the restart read them from it rather than comparing again.
    kept["pairs"] = []
    _kept(tmp_path).write_text(json.dumps(kept))
    keep_on_disk(_kept(tmp_path))

    assert _listed(client) == []


def test_a_restart_compares_what_changed_since(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    _image(db, "a", 0)
    assert _listed(client) == []
    keep_on_disk(_kept(tmp_path))

    _image(db, "b", 1)

    assert _listed(client) == ["a", "b"]


def test_an_unreadable_file_on_disk_is_compared_again(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    _image(db, "a", 0)
    _image(db, "b", 1)
    _kept(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    _kept(tmp_path).write_text("{not json")
    keep_on_disk(_kept(tmp_path))

    assert _listed(client) == ["a", "b"]
