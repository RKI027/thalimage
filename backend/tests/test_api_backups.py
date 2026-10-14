"""Tests for the /backups endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

DEFAULTS = {"enabled": True, "time": "06:00", "keep": 7}


def test_status_defaults(client: TestClient) -> None:
    assert client.get("/api/v1/backups").json() == {
        "config": DEFAULTS,
        "last": None,
        "running": False,
    }


def test_config_round_trips(client: TestClient) -> None:
    resp = client.patch("/api/v1/backups", json={"time": "05:45", "keep": 3})
    assert resp.status_code == 200
    assert resp.json()["config"] == {"enabled": True, "time": "05:45", "keep": 3}
    assert client.get("/api/v1/backups").json()["config"]["time"] == "05:45"


def test_bad_config_is_422(client: TestClient) -> None:
    assert client.patch("/api/v1/backups", json={"time": "25:00"}).status_code == 422
    assert client.patch("/api/v1/backups", json={"keep": 0}).status_code == 422
    assert client.get("/api/v1/backups").json()["config"] == DEFAULTS


def test_run_now_takes_and_reports_a_backup(client: TestClient, tmp_path: Path) -> None:
    resp = client.post("/api/v1/backups/run")
    assert resp.status_code == 200
    record = resp.json()
    assert record["error"] is None
    assert (tmp_path / "db_backups" / record["file"]).stat().st_size == record["size"]
    assert client.get("/api/v1/backups").json()["last"] == record
