"""Tests for /api/v1/sources endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_list_sources_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_source(client: TestClient, image_dir: Path) -> None:
    resp = client.post("/api/v1/sources", json={
        "path": str(image_dir),
        "label": "test",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "test"
    assert data["recursive"] is True
    assert data["enabled"] is True


def test_create_source_nonexistent_dir(client: TestClient) -> None:
    resp = client.post("/api/v1/sources", json={"path": "/nonexistent/dir"})
    assert resp.status_code == 400


def test_create_source_duplicate(client: TestClient, image_dir: Path) -> None:
    client.post("/api/v1/sources", json={"path": str(image_dir)})
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    assert resp.status_code == 409


def test_delete_source(client: TestClient, image_dir: Path) -> None:
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    source_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/sources/{source_id}")
    assert resp.status_code == 204

    resp = client.get("/api/v1/sources")
    assert resp.json() == []


def test_delete_source_not_found(client: TestClient) -> None:
    resp = client.delete("/api/v1/sources/999")
    assert resp.status_code == 404


def test_trigger_scan(client: TestClient, image_dir: Path) -> None:
    resp = client.post("/api/v1/sources", json={"path": str(image_dir)})
    source_id = resp.json()["id"]

    resp = client.post(f"/api/v1/sources/{source_id}/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scanned"] == 3
    assert data["added"] == 3
    assert data["errors"] == 0


def test_trigger_scan_not_found(client: TestClient) -> None:
    resp = client.post("/api/v1/sources/999/scan")
    assert resp.status_code == 404
