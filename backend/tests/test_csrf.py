"""Cross-site pages cannot make the server write (SEC-002)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import thalimage.app as app_module
from thalimage.config import Settings


@pytest.fixture
def guarded(client: TestClient, image_dir: Path) -> tuple[TestClient, int]:
    source = client.post("/api/v1/sources", json={"path": str(image_dir)}).json()["id"]
    return client, source


def test_cross_site_scan_trigger_is_refused(guarded: tuple[TestClient, int]) -> None:
    client, source = guarded
    for headers in (
        {"origin": "https://evil.example"},
        {"sec-fetch-site": "cross-site"},
        {"origin": "null"},
    ):
        resp = client.post(f"/api/v1/sources/{source}/scan", headers=headers)
        assert resp.status_code == 403, headers


def test_cross_site_json_writes_are_refused(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/tags", json={"name": "x"}, headers={"origin": "https://evil.example"}
    )
    assert resp.status_code == 403
    assert client.get("/api/v1/tags").json() == []


def test_same_origin_and_non_browser_writes_pass(guarded: tuple[TestClient, int]) -> None:
    client, _ = guarded
    for i, headers in enumerate(
        (
            {"origin": "http://127.0.0.1", "sec-fetch-site": "same-origin"},
            {"sec-fetch-site": "none"},  # typed into the address bar, bookmarks
            {},  # curl, scripts
        )
    ):
        resp = client.post("/api/v1/tags", json={"name": f"t{i}"}, headers=headers)
        assert resp.status_code == 201, headers


def test_reads_are_not_affected(client: TestClient) -> None:
    resp = client.get("/api/v1/tags", headers={"origin": "https://evil.example"})
    assert resp.status_code == 200


def _app_with(monkeypatch: pytest.MonkeyPatch, **settings: object) -> TestClient:
    monkeypatch.setattr(app_module, "get_settings", lambda: Settings(**settings))
    # No lifespan: the guard answers before any route or DB is involved.
    return TestClient(
        app_module.create_app(), base_url="http://127.0.0.1", raise_server_exceptions=False
    )


def test_origins_of_allowed_hosts_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Behind tailscale serve the page is https://box.tail1234.ts.net."""
    client = _app_with(monkeypatch, allowed_hosts=["*.ts.net"])
    ok = client.delete(
        "/api/v1/tags/999",
        headers={"host": "box.tail1234.ts.net", "origin": "https://box.tail1234.ts.net"},
    )
    assert ok.status_code != 403
    other = client.delete(
        "/api/v1/tags/999",
        headers={"host": "box.tail1234.ts.net", "origin": "https://evil.example"},
    )
    assert other.status_code == 403


def test_configured_cors_origins_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _app_with(monkeypatch, cors_origins=["https://tools.example"])
    resp = client.delete(
        "/api/v1/tags/999",
        headers={"origin": "https://tools.example", "sec-fetch-site": "cross-site"},
    )
    assert resp.status_code != 403
