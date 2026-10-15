"""Tests for response compression."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import thalimage.app as app_module
from thalimage.config import Settings

# Large and repetitive enough to be worth compressing.
TEXT = "thalimage " * 200
GZIP = {"Accept-Encoding": "gzip"}


@pytest.fixture
def build_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client serving a temp frontend build holding one file of each kind."""
    build = tmp_path / "build"
    (build / "_app").mkdir(parents=True)
    (build / "index.html").write_text(TEXT)
    (build / "_app" / "entry.js").write_text(TEXT)
    (build / "_app" / "data.json").write_text(f'"{TEXT}"')
    (build / "_app" / "picture.webp").write_bytes(TEXT.encode())
    (build / "_app" / "clip.mp4").write_bytes(TEXT.encode())
    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: Settings(allowed_hosts=[], cors_origins=[], frontend_dir=build),
    )
    return TestClient(app_module.create_app(), base_url="http://127.0.0.1")


@pytest.mark.parametrize("path", ["/", "/_app/entry.js", "/_app/data.json"])
def test_text_responses_are_compressed(build_client: TestClient, path: str) -> None:
    resp = build_client.get(path, headers=GZIP)
    assert resp.headers.get("content-encoding") == "gzip"
    assert TEXT in resp.text


def test_api_json_is_compressed(build_client: TestClient) -> None:
    # The OpenAPI schema is a large JSON response that needs no database.
    resp = build_client.get("/api/openapi.json", headers=GZIP)
    assert resp.headers.get("content-encoding") == "gzip"
    assert resp.json()["info"]["title"] == "Thalimage"


@pytest.mark.parametrize("path", ["/_app/picture.webp", "/_app/clip.mp4"])
def test_media_is_sent_as_is(build_client: TestClient, path: str) -> None:
    resp = build_client.get(path, headers=GZIP)
    assert "content-encoding" not in resp.headers
    assert resp.content == TEXT.encode()


def test_partial_content_is_sent_as_is(build_client: TestClient) -> None:
    # A range's offsets count the file's own bytes.
    resp = build_client.get("/_app/entry.js", headers={**GZIP, "Range": "bytes=0-999"})
    assert resp.status_code == 206
    assert "content-encoding" not in resp.headers
    assert resp.content == TEXT.encode()[:1000]


def test_nothing_is_compressed_for_a_client_that_did_not_ask(build_client: TestClient) -> None:
    resp = build_client.get("/", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in resp.headers


def test_scan_progress_stream_is_not_compressed(client: TestClient, image_dir: Path) -> None:
    # A gzip stream would hold events back until its buffer fills.
    source_id = client.post("/api/v1/sources", json={"path": str(image_dir)}).json()["id"]
    client.post(f"/api/v1/sources/{source_id}/scan")
    resp = client.get(f"/api/v1/sources/{source_id}/scan/status", headers=GZIP)
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "content-encoding" not in resp.headers
