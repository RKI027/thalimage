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
