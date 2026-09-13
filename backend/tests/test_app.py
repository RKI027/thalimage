"""Tests for the FastAPI app factory, including the SPA static fallback."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import thalimage.app as app_module
from thalimage.config import Settings


@pytest.fixture
def spa_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client whose frontend build dir is a controlled temp tree."""
    build = tmp_path / "build"
    (build / "_app").mkdir(parents=True)
    (build / "index.html").write_text("INDEX")
    (build / "foo.txt").write_text("FOO")
    # A file that lives outside the build dir and must never be served.
    (tmp_path / "secret.txt").write_text("SECRET")

    monkeypatch.setattr(app_module, "FRONTEND_DIR", build)
    # Pin settings so the Host allowlist is deterministic regardless of any
    # local config.toml. init kwargs take precedence over env/toml sources.
    monkeypatch.setattr(
        app_module, "get_settings", lambda: Settings(allowed_hosts=[], cors_origins=[])
    )
    # Construct without the context manager so lifespan (which opens the real
    # DB) does not run; the static fallback does not need app state.
    # Loopback base_url satisfies the always-allowed Host check.
    return TestClient(app_module.create_app(), base_url="http://127.0.0.1")


def test_serves_existing_build_file(spa_client: TestClient) -> None:
    resp = spa_client.get("/foo.txt")
    assert resp.status_code == 200
    assert resp.text == "FOO"


def test_unknown_path_falls_back_to_index(spa_client: TestClient) -> None:
    resp = spa_client.get("/some/client/route")
    assert resp.status_code == 200
    assert resp.text == "INDEX"


def test_traversal_does_not_escape_build_dir(spa_client: TestClient) -> None:
    # Percent-encoded dot-segments survive client-side normalization and reach
    # the route as ../secret.txt; the handler must not serve the outside file.
    resp = spa_client.get("/%2e%2e/secret.txt")
    assert "SECRET" not in resp.text
    assert resp.text == "INDEX"


def test_loopback_host_is_allowed(spa_client: TestClient) -> None:
    resp = spa_client.get("/foo.txt")
    assert resp.status_code == 200


def test_unexpected_host_is_rejected(spa_client: TestClient) -> None:
    resp = spa_client.get("/foo.txt", headers={"host": "evil.example"})
    assert resp.status_code == 400


def test_unknown_api_path_returns_json_404(spa_client: TestClient) -> None:
    """The SPA fallback must not answer for the API namespace."""
    resp = spa_client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def test_unknown_api_path_is_404_for_any_depth(spa_client: TestClient) -> None:
    for path in ("/api", "/api/", "/api/v1/docs/a/b", "/api/v99/whatever"):
        resp = spa_client.get(path)
        assert resp.status_code == 404, path
        assert "INDEX" not in resp.text, path


def test_spa_fallback_still_serves_app_routes(spa_client: TestClient) -> None:
    """A client-side route that merely starts with 'api' is not the API."""
    resp = spa_client.get("/apiary")
    assert resp.status_code == 200
    assert resp.text == "INDEX"


def test_openapi_explorer_lives_under_the_api_prefix(spa_client: TestClient) -> None:
    """The /docs URL belongs to the in-app documentation, not to Swagger."""
    assert spa_client.get("/api/docs").status_code == 200
    assert spa_client.get("/api/openapi.json").status_code == 200


def test_docs_url_is_left_to_the_frontend(spa_client: TestClient) -> None:
    resp = spa_client.get("/docs")
    assert resp.text == "INDEX"
