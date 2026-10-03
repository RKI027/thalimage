"""Tests for /api/v1/sources endpoints."""

from pathlib import Path

import json

from fastapi.testclient import TestClient

from thalimage.deps import get_scan_manager


def _last_status(client: TestClient, source_id: int) -> dict:
    """Read the scan status stream to its end; return the last event's data."""
    resp = client.get(f"/api/v1/sources/{source_id}/scan/status")
    assert resp.status_code == 200
    events = [
        json.loads(line[len("data: "):])
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    return events[-1]


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
    assert resp.status_code == 202
    assert resp.json()["status"] == "started"
    # Drain the status stream so the scan thread is done before teardown.
    assert _last_status(client, source_id)["phase"] == "complete"


def test_trigger_scan_not_found(client: TestClient) -> None:
    resp = client.post("/api/v1/sources/999/scan")
    assert resp.status_code == 404


def test_trigger_scan_while_running_is_409(client: TestClient, image_dir: Path) -> None:
    source_id = client.post("/api/v1/sources", json={"path": str(image_dir)}).json()["id"]
    scan_manager = client.app.dependency_overrides[get_scan_manager]()  # type: ignore[attr-defined]
    scan_manager.start(source_id)
    assert client.post(f"/api/v1/sources/{source_id}/scan").status_code == 409


def test_failed_scan_reports_error(
    client: TestClient, image_dir: Path, monkeypatch
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("thalimage.api.sources.run_scan", boom)
    source_id = client.post("/api/v1/sources", json={"path": str(image_dir)}).json()["id"]
    assert client.post(f"/api/v1/sources/{source_id}/scan").status_code == 202
    status = _last_status(client, source_id)
    assert status["phase"] == "error"
    assert status["message"] == "disk on fire"


def test_scan_status_unknown_source_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/sources/999/scan/status").status_code == 404


def test_scan_status_never_scanned_is_idle(client: TestClient, image_dir: Path) -> None:
    source_id = client.post("/api/v1/sources", json={"path": str(image_dir)}).json()["id"]
    assert _last_status(client, source_id) == {"phase": "idle"}
