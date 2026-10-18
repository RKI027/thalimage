"""Tests for the /settings endpoints (TST-005)."""

import sqlite3

from fastapi.testclient import TestClient


def test_defaults(client: TestClient) -> None:
    assert client.get("/api/v1/settings").json() == {
        "show_nsfw": False,
        "edit_threshold": 0.25,
        "near_duplicate_threshold": 0.15,
    }


def test_show_nsfw_round_trips(client: TestClient, db: sqlite3.Connection) -> None:
    resp = client.patch("/api/v1/settings", json={"show_nsfw": True})
    assert resp.status_code == 200
    assert resp.json()["show_nsfw"] is True
    assert client.get("/api/v1/settings").json()["show_nsfw"] is True
    stored = db.execute("SELECT value FROM settings WHERE key = 'show_nsfw'").fetchone()[0]
    assert stored == "true"

    client.patch("/api/v1/settings", json={"show_nsfw": False})
    assert client.get("/api/v1/settings").json() == {
        "show_nsfw": False,
        "edit_threshold": 0.25,
        "near_duplicate_threshold": 0.15,
    }


def test_empty_patch_changes_nothing(client: TestClient) -> None:
    client.patch("/api/v1/settings", json={"show_nsfw": True})
    assert client.patch("/api/v1/settings", json={}).json()["show_nsfw"] is True


def test_wrong_type_is_422(client: TestClient) -> None:
    assert client.patch("/api/v1/settings", json={"show_nsfw": "maybe"}).status_code == 422


def test_edit_threshold_round_trips(client: TestClient) -> None:
    resp = client.patch("/api/v1/settings", json={"edit_threshold": 0.1})
    assert resp.json()["edit_threshold"] == 0.1
    assert client.get("/api/v1/settings").json()["edit_threshold"] == 0.1


def test_edit_threshold_outside_0_to_1_is_422(client: TestClient) -> None:
    for value in (-0.1, 1.5):
        assert client.patch("/api/v1/settings", json={"edit_threshold": value}).status_code == 422


def test_near_duplicate_threshold_round_trips(client: TestClient) -> None:
    resp = client.patch("/api/v1/settings", json={"near_duplicate_threshold": 0.2})
    assert resp.json()["near_duplicate_threshold"] == 0.2
    assert client.get("/api/v1/settings").json()["near_duplicate_threshold"] == 0.2


def test_near_duplicate_threshold_outside_0_to_the_cap_is_422(client: TestClient) -> None:
    for value in (-0.1, 0.31):
        resp = client.patch("/api/v1/settings", json={"near_duplicate_threshold": value})
        assert resp.status_code == 422
