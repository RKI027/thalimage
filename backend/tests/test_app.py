"""Tests for the FastAPI app factory, including the SPA static fallback."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import thalimage.app as app_module


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
    # Construct without the context manager so lifespan (which opens the real
    # DB) does not run; the static fallback does not need app state.
    return TestClient(app_module.create_app())


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
