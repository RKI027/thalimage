"""Tests for /api/v1/collections endpoints."""

import time
from pathlib import Path

from fastapi.testclient import TestClient


def _seed_images(client: TestClient, image_dir: Path) -> list[str]:
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    source_id = resp.json()["id"]
    client.post(f"/api/v1/sources/{source_id}/scan")

    for _ in range(50):
        resp = client.get("/api/v1/images")
        items = resp.json()["items"]
        if items:
            return [img["content_hash"] for img in items]
        time.sleep(0.1)

    return []


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
    hashes = _seed_images(client, image_dir)
    resp = client.post("/api/v1/collections", json={"name": "Album"})
    cid = resp.json()["id"]

    resp = client.post(f"/api/v1/collections/{cid}/images", json={"hashes": hashes[:2]})
    assert resp.status_code == 200
    assert resp.json()["added"] == 2

    resp = client.get(f"/api/v1/collections/{cid}")
    assert resp.json()["image_count"] == 2


def test_remove_images_from_collection(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)
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


def test_filter_images_by_collection(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)
    resp = client.post("/api/v1/collections", json={"name": "Subset"})
    cid = resp.json()["id"]
    client.post(f"/api/v1/collections/{cid}/images", json={"hashes": [hashes[0]]})

    resp = client.get(f"/api/v1/images?collection_id={cid}")
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["content_hash"] == hashes[0]
