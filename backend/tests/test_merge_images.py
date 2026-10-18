"""Merging images into another: the merged images' files are deleted from
disk, and their tags, collections, votes and file versions go to the image
kept. Votes between the merged images and the one kept are dropped."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers import scan_source


@pytest.fixture
def library(client: TestClient, image_dir: Path) -> tuple[int, dict[str, str]]:
    """The fixture images scanned into one writable source: its id, and the
    keys by file name."""
    source_id, _ = scan_source(client, image_dir)
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": True})
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    return source_id, {i["filename"]: i["content_hash"] for i in items}


def _merge(client: TestClient, kept: str, *merged: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/images/{kept}/merge", json={"hashes": list(merged)})


def _tag(client: TestClient, content_hash: str, name: str) -> None:
    tag_id = client.post("/api/v1/tags", json={"name": name}).json()["id"]
    client.post(f"/api/v1/images/{content_hash}/tags", json={"tag_id": tag_id})


def _tags(client: TestClient, content_hash: str) -> set[str]:
    return {t["name"] for t in client.get(f"/api/v1/images/{content_hash}/tags").json()}


def test_merging_deletes_the_merged_files_and_keeps_their_tags(
    client: TestClient, image_dir: Path, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library
    kept, merged = keys["a.png"], keys["b.jpg"]
    _tag(client, kept, "kept")
    _tag(client, merged, "merged")

    resp = _merge(client, kept, merged)

    assert resp.status_code == 200
    assert resp.json() == {"merged": [merged], "deleted": 1, "sidecars": 0, "failed": []}
    assert not (image_dir / "b.jpg").exists()
    assert (image_dir / "a.png").exists()
    assert _tags(client, kept) == {"kept", "merged"}
    assert client.get(f"/api/v1/images/{merged}").status_code == 404


def test_the_merged_images_collections_go_to_the_image_kept(
    client: TestClient, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library
    kept, merged = keys["a.png"], keys["b.jpg"]
    cid = client.post("/api/v1/collections", json={"name": "Picks"}).json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [merged]})

    _merge(client, kept, merged)

    listed = client.get("/api/v1/images", params={"collection_id": cid}).json()["items"]
    assert [i["content_hash"] for i in listed] == [kept]


def test_votes_move_to_the_image_kept_except_those_between_the_two(
    client: TestClient, db: sqlite3.Connection, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library
    kept, merged, other = keys["a.png"], keys["b.jpg"], keys["c.png"]
    cid = client.post("/api/v1/collections", json={"name": "Votes"}).json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [kept, merged, other]})
    for winner, loser in ((merged, kept), (merged, other)):
        client.post(f"/api/v1/collections/{cid}/elo/vote", json={"winner_hash": winner, "loser_hash": loser})

    _merge(client, kept, merged)

    votes = db.execute("SELECT winner_hash, loser_hash FROM votes").fetchall()
    assert [tuple(v) for v in votes] == [(kept, other)]


def test_merging_several_images_at_once(
    client: TestClient, image_dir: Path, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library
    kept = keys["a.png"]

    resp = _merge(client, kept, keys["b.jpg"], keys["c.png"], kept)

    assert sorted(resp.json()["merged"]) == sorted([keys["b.jpg"], keys["c.png"]])
    assert client.get("/api/v1/images").json()["total_count"] == 1


def test_nothing_merges_unless_every_merged_file_can_be_deleted(
    client: TestClient, image_dir: Path, library: tuple[int, dict[str, str]]
) -> None:
    source_id, keys = library
    kept, merged = keys["a.png"], keys["b.jpg"]
    _tag(client, merged, "merged")
    client.patch(f"/api/v1/sources/{source_id}", json={"writable": False})

    resp = _merge(client, kept, merged)

    assert resp.status_code == 409
    assert (image_dir / "b.jpg").exists()
    assert _tags(client, merged) == {"merged"}
    assert _tags(client, kept) == set()


def test_merging_into_an_unknown_image_is_404(
    client: TestClient, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library

    assert _merge(client, "0" * 64, keys["b.jpg"]).status_code == 404


def test_the_merged_images_file_versions_stay_with_the_image_kept(
    client: TestClient, db: sqlite3.Connection, library: tuple[int, dict[str, str]]
) -> None:
    _, keys = library
    kept, merged = keys["a.png"], keys["b.jpg"]
    versions = db.execute("SELECT file_hash FROM file_metadata WHERE content_hash = ?", (merged,)).fetchall()
    assert versions

    _merge(client, kept, merged)

    kept_versions = {
        r[0] for r in db.execute("SELECT file_hash FROM file_metadata WHERE content_hash = ?", (kept,))
    }
    assert {v[0] for v in versions} <= kept_versions
