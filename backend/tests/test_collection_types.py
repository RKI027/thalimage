"""Tests for collection type system (presets, source presets)."""

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient


def _create_source(client: TestClient, image_dir: Path) -> int:
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    return resp.json()["id"]


def _seed_images(client: TestClient, image_dir: Path) -> tuple[int, list[str]]:
    source_id = _create_source(client, image_dir)
    client.post(f"/api/v1/sources/{source_id}/scan")
    for _ in range(50):
        resp = client.get("/api/v1/images")
        items = resp.json()["items"]
        if items:
            return source_id, [img["content_hash"] for img in items]
        time.sleep(0.1)
    return source_id, []


# --- Service-level tests via API ---


def test_collections_have_type_field(client: TestClient) -> None:
    """Manual collections should have type='manual' by default."""
    resp = client.post("/api/v1/collections", json={"name": "Test"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "manual"
    assert data["source_id"] is None


def test_list_collections_filter_by_type(client: TestClient) -> None:
    """Can filter collections by type."""
    client.post("/api/v1/collections", json={"name": "Manual One"})
    client.post("/api/v1/collections", json={"name": "Manual Two"})

    resp = client.get("/api/v1/collections?type=manual")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/v1/collections?type=source_preset")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_delete_preset_forbidden(
    client: TestClient, db: sqlite3.Connection, image_dir: Path
) -> None:
    """Deleting a source preset collection should be forbidden."""
    source_id, _ = _seed_images(client, image_dir)

    # Find the auto-created preset
    resp = client.get("/api/v1/collections?type=source_preset")
    presets = resp.json()
    assert len(presets) >= 1
    preset_id = presets[0]["id"]

    resp = client.delete(f"/api/v1/collections/{preset_id}")
    assert resp.status_code == 403


def test_rename_preset_forbidden(
    client: TestClient, image_dir: Path
) -> None:
    """Renaming a source preset collection should be forbidden."""
    _seed_images(client, image_dir)

    resp = client.get("/api/v1/collections?type=source_preset")
    preset_id = resp.json()[0]["id"]

    resp = client.patch(
        f"/api/v1/collections/{preset_id}", json={"name": "New Name"}
    )
    assert resp.status_code == 403


def test_preset_sort_change_allowed(
    client: TestClient, image_dir: Path
) -> None:
    """Changing sort on a preset should be allowed."""
    _seed_images(client, image_dir)

    resp = client.get("/api/v1/collections?type=source_preset")
    preset_id = resp.json()[0]["id"]

    resp = client.patch(
        f"/api/v1/collections/{preset_id}",
        json={"sort_by": "date_modified", "sort_dir": "desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["sort_by"] == "date_modified"


def test_source_preset_has_images_after_scan(
    client: TestClient, image_dir: Path
) -> None:
    """After scanning, the source preset should contain all scanned images."""
    source_id, hashes = _seed_images(client, image_dir)

    resp = client.get("/api/v1/collections?type=source_preset")
    presets = [p for p in resp.json() if p["source_id"] == source_id]
    assert len(presets) == 1
    assert presets[0]["image_count"] == len(hashes)


def test_source_preset_created_on_source_creation(
    client: TestClient, image_dir: Path
) -> None:
    """Creating a source should also create its preset collection."""
    source_id = _create_source(client, image_dir)

    resp = client.get("/api/v1/collections?type=source_preset")
    presets = [p for p in resp.json() if p["source_id"] == source_id]
    assert len(presets) == 1
    assert presets[0]["image_count"] == 0  # no scan yet


def test_source_deletion_removes_preset(
    client: TestClient, image_dir: Path
) -> None:
    """Deleting a source should also delete its preset collection."""
    source_id, _ = _seed_images(client, image_dir)

    resp = client.get("/api/v1/collections?type=source_preset")
    assert any(p["source_id"] == source_id for p in resp.json())

    client.delete(f"/api/v1/sources/{source_id}")

    resp = client.get("/api/v1/collections?type=source_preset")
    assert not any(p["source_id"] == source_id for p in resp.json())


def test_get_or_create_preset_idempotent(
    client: TestClient, image_dir: Path
) -> None:
    """Creating a source and scanning twice should not duplicate presets."""
    source_id = _create_source(client, image_dir)

    # Scan twice
    client.post(f"/api/v1/sources/{source_id}/scan")
    for _ in range(50):
        resp = client.get("/api/v1/images")
        if resp.json()["items"]:
            break
        time.sleep(0.1)

    client.post(f"/api/v1/sources/{source_id}/scan")
    time.sleep(1)

    resp = client.get("/api/v1/collections?type=source_preset")
    presets = [p for p in resp.json() if p["source_id"] == source_id]
    assert len(presets) == 1
