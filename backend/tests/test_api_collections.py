"""Tests for /api/v1/collections endpoints."""

import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


from tests.helpers import insert_image, scan_source


def test_list_collections_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/collections")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_collection(client: TestClient) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Favorites"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Favorites"
    assert data["image_count"] == 0


def test_get_collection(client: TestClient) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Test"})
    cid = resp.json()["id"]

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test"


def test_get_collection_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/collections/999")
    assert resp.status_code == 404


def test_update_collection(client: TestClient) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Old"})
    cid = resp.json()["id"]

    resp = client.patch(f"/api/v1/collections/{cid}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_delete_collection(client: TestClient) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Temp"})
    cid = resp.json()["id"]

    resp = client.delete(f"/api/v1/collections/{cid}")
    assert resp.status_code == 204

    resp = client.get("/api/v1/collections")
    assert resp.json() == []


def test_delete_collection_not_found(client: TestClient) -> None:
    resp = client.delete("/api/v1/collections/999")
    assert resp.status_code == 404


def test_add_images_to_collection(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.post("/api/v1/collections", json={"name": "Album"})
    cid = resp.json()["id"]

    resp = client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes[:2]})
    assert resp.status_code == 200
    assert resp.json()["added"] == 2

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.json()["image_count"] == 2


def test_add_images_count_excludes_duplicates(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    cid = client.post("/api/v1/collections", json={"name": "Album"}).json()["id"]

    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes[:2]})
    # Re-adding the same two plus one new one should count only the new one.
    resp = client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    assert resp.json()["added"] == 1

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.json()["image_count"] == len(hashes)


def test_remove_images_from_collection(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.post("/api/v1/collections", json={"name": "Album"})
    cid = resp.json()["id"]

    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    resp = client.request(
        "DELETE",
        f"/api/v1/collections/{cid}/images",
        json={"hashes": [hashes[0]]},
    )
    assert resp.status_code == 200
    assert resp.json()["removed"] == 1

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.json()["image_count"] == 2


def test_update_collection_sort_persists(client: TestClient) -> None:
    resp = client.post("/api/v1/collections", json={"name": "Sorted"})
    cid = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/collections/{cid}",
        json={"sort_by": "date_modified", "sort_dir": "desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sort_by"] == "date_modified"
    assert data["sort_dir"] == "desc"

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.json()["sort_by"] == "date_modified"
    assert resp.json()["sort_dir"] == "desc"


def test_filter_images_by_collection(client: TestClient, image_dir: Path) -> None:
    hashes = scan_source(client, image_dir)[1]
    resp = client.post("/api/v1/collections", json={"name": "Subset"})
    cid = resp.json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [hashes[0]]})

    resp = client.get(f"/api/v1/images?collection_id={cid}")
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["content_hash"] == hashes[0]


def _rescan(client: TestClient, source_id: int) -> None:
    client.post(f"/api/v1/sources/{source_id}/scan")
    client.get(f"/api/v1/sources/{source_id}/scan/status")


def _archive(client: TestClient, content_hash: str) -> None:
    client.patch(f"/api/v1/images/{content_hash}/archive", json={"archived": True})


def test_collection_counts_archived_images_apart(client: TestClient, image_dir: Path) -> None:
    """The count matches what browsing shows; archived images are counted on their own."""
    hashes = scan_source(client, image_dir)[1]
    cid = client.post("/api/v1/collections", json={"name": "Album"}).json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    _archive(client, hashes[0])

    data = client.get(f"/api/v1/collections/{cid}").json()
    shown = client.get("/api/v1/images", params={"collection_id": cid}).json()["total_count"]
    assert (data["image_count"], data["archived_count"]) == (shown, 1)
    assert shown == len(hashes) - 1


def test_source_preset_counts_archived_images_apart(
    client: TestClient, image_dir: Path
) -> None:
    source_id, hashes = scan_source(client, image_dir)
    _archive(client, hashes[0])

    presets = client.get("/api/v1/collections?type=source_preset").json()
    preset = next(p for p in presets if p["source_id"] == source_id)
    assert (preset["image_count"], preset["archived_count"]) == (len(hashes) - 1, 1)


def test_collection_count_skips_images_whose_file_is_gone(
    client: TestClient, image_dir: Path
) -> None:
    source_id, hashes = scan_source(client, image_dir)
    cid = client.post("/api/v1/collections", json={"name": "Album"}).json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes})
    victim = client.get(f"/api/v1/images/{hashes[0]}").json()["filename"]
    (image_dir / victim).unlink()
    _rescan(client, source_id)

    data = client.get(f"/api/v1/collections/{cid}").json()
    assert (data["image_count"], data["archived_count"]) == (len(hashes) - 1, 0)


def test_source_preset_counts_copies_in_one_source_once(
    client: TestClient, db: sqlite3.Connection, image_dir: Path
) -> None:
    source_id, hashes = scan_source(client, image_dir)
    first = client.get(f"/api/v1/images/{hashes[0]}").json()["filename"]
    (image_dir / "copy").mkdir()
    shutil.copy(image_dir / first, image_dir / "copy" / first)
    _rescan(client, source_id)
    copies = db.execute(
        "SELECT COUNT(*) FROM image_locations WHERE content_hash = ?", (hashes[0],)
    ).fetchone()[0]
    assert copies == 2

    presets = client.get("/api/v1/collections?type=source_preset").json()
    preset = next(p for p in presets if p["source_id"] == source_id)
    assert preset["image_count"] == len(hashes)


def test_labels_lists_each_image_with_its_tags_in_the_namespaces_asked(
    client: TestClient, db: sqlite3.Connection
) -> None:
    a, b, c = (insert_image(db, ch * 64) for ch in "abc")
    cid = client.post("/api/v1/collections", json={"name": "Labelling"}).json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [b, a, c]})
    for name, hashes in (("medium:photographic", [a, b]), ("rating:sfw", [a]), ("landscape", [a, c])):
        tid = client.post("/api/v1/tags", json={"name": name}).json()["id"]
        client.post(f"/api/v1/tags/{tid}/images", json={"hashes": hashes})
    db.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (c,))
    db.commit()

    resp = client.get(f"/api/v1/collections/{cid}/labels", params={"namespace": ["medium", "rating"]})

    assert resp.status_code == 200
    assert resp.json() == [
        {"content_hash": b, "labels": ["medium:photographic"]},
        {"content_hash": a, "labels": ["medium:photographic", "rating:sfw"]},
    ]


def test_labels_of_an_unknown_collection_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/collections/999/labels").status_code == 404
