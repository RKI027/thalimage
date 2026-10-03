"""Tests for the /settings endpoints (TST-005)."""

import sqlite3

from fastapi.testclient import TestClient


def test_defaults(client: TestClient) -> None:
    assert client.get("/api/v1/settings").json() == {"show_nsfw": False}


def test_show_nsfw_round_trips(client: TestClient, db: sqlite3.Connection) -> None:
    resp = client.patch("/api/v1/settings", json={"show_nsfw": True})
    assert resp.status_code == 200
    assert resp.json() == {"show_nsfw": True}
    assert client.get("/api/v1/settings").json() == {"show_nsfw": True}
    stored = db.execute("SELECT value FROM settings WHERE key = 'show_nsfw'").fetchone()[0]
    assert stored == "true"

    client.patch("/api/v1/settings", json={"show_nsfw": False})
    assert client.get("/api/v1/settings").json() == {"show_nsfw": False}


def test_empty_patch_changes_nothing(client: TestClient) -> None:
    client.patch("/api/v1/settings", json={"show_nsfw": True})
    assert client.patch("/api/v1/settings", json={}).json() == {"show_nsfw": True}


def test_wrong_type_is_422(client: TestClient) -> None:
    assert client.patch("/api/v1/settings", json={"show_nsfw": "maybe"}).status_code == 422
