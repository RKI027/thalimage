"""Tests for /api/v1/images endpoints."""

import time
from pathlib import Path

from fastapi.testclient import TestClient


def _seed_images(client: TestClient, image_dir: Path) -> list[str]:
    """Create source + scan, return list of content hashes."""
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    source_id = resp.json()["id"]
    client.post(f"/api/v1/sources/{source_id}/scan")

    # Wait for async scan to complete
    for _ in range(50):
        resp = client.get("/api/v1/images")
        items = resp.json()["items"]
        if items:
            return [img["content_hash"] for img in items]
        time.sleep(0.1)

    return []


def test_list_images_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/images")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_count"] == 0
    assert data["next_cursor"] is None


def test_list_images_after_scan(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)
    assert len(hashes) == 3

    resp = client.get("/api/v1/images")
    data = resp.json()
    assert data["total_count"] == 3
    assert len(data["items"]) == 3


def test_list_images_pagination(client: TestClient, image_dir: Path) -> None:
    _seed_images(client, image_dir)

    resp = client.get("/api/v1/images?limit=2")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None

    resp2 = client.get(f"/api/v1/images?limit=2&cursor={data['next_cursor']}")
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["next_cursor"] is None


def test_list_images_sort_desc(client: TestClient, image_dir: Path) -> None:
    _seed_images(client, image_dir)

    asc = client.get("/api/v1/images?sort=name&dir=asc").json()
    desc = client.get("/api/v1/images?sort=name&dir=desc").json()
    asc_names = [i["filename"] for i in asc["items"]]
    desc_names = [i["filename"] for i in desc["items"]]
    assert asc_names == list(reversed(desc_names))


def test_get_image_detail(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)

    resp = client.get(f"/api/v1/images/{hashes[0]}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_hash"] == hashes[0]
    assert "width" in data
    assert "height" in data


def test_get_image_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/images/nonexistent")
    assert resp.status_code == 404


def test_get_image_file(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)
    resp = client.get(f"/api/v1/images/{hashes[0]}/file")
    assert resp.status_code == 200
    assert len(resp.content) > 0


def test_get_image_thumb(client: TestClient, image_dir: Path) -> None:
    hashes = _seed_images(client, image_dir)
    resp = client.get(f"/api/v1/images/{hashes[0]}/thumb")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"


def test_get_thumb_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/images/nonexistent/thumb")
    assert resp.status_code == 404
