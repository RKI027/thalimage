"""Tests for the /api/v1/version endpoint."""

from fastapi.testclient import TestClient


def test_version_reports_version_and_commit(client: TestClient) -> None:
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"]
    # commit is null in a build made without a checkout
    assert "commit" in body


def test_version_matches_the_running_package(client: TestClient) -> None:
    from thalimage.version import version_info

    assert client.get("/api/v1/version").json()["version"] == version_info().version


def test_openapi_version_matches_the_package(client: TestClient) -> None:
    """The schema version is derived, not a second literal to drift."""
    from thalimage.version import version_info

    schema = client.get("/api/openapi.json").json()
    assert schema["info"]["version"] == version_info().version


def test_the_frontend_carries_no_second_version() -> None:
    """pyproject.toml is the one place the version is written (PKG-005)."""
    import json
    from pathlib import Path

    import pytest

    package_json = Path(__file__).resolve().parents[2] / "frontend" / "package.json"
    if not package_json.exists():
        pytest.skip("backend-only checkout")
    assert "version" not in json.loads(package_json.read_text())
