"""Shared test fixtures."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from thalimage.app import create_app
from thalimage.deps import get_db, open_db, get_preview_dir, get_scan_manager, get_thumb_dir
from thalimage.db.engine import connect, migrate
from thalimage.services.scan_manager import ScanManager


@pytest.fixture
def db(tmp_path: Path):
    """A migrated in-memory-like SQLite connection."""
    conn = connect(tmp_path / "test.db", check_same_thread=False)
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db: sqlite3.Connection, tmp_path: Path):
    """FastAPI test client with overridden DB and thumb dir."""
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    preview_dir = tmp_path / "previews"
    preview_dir.mkdir()

    scan_manager = ScanManager()
    app = create_app()

    # Each request gets its own connection to the test database, as in
    # production; `db` is just another connection to the same file.
    def _test_db() -> Iterator[sqlite3.Connection]:
        yield from open_db(tmp_path / "test.db")

    app.dependency_overrides[get_db] = _test_db
    app.dependency_overrides[get_thumb_dir] = lambda: thumb_dir
    app.dependency_overrides[get_preview_dir] = lambda: preview_dir
    app.dependency_overrides[get_scan_manager] = lambda: scan_manager

    # base_url drives the Host header; use loopback so TrustedHostMiddleware
    # (which always allows loopback) accepts it.
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """Create a small 4x3 red PNG with known dimensions."""
    img = Image.new("RGB", (4, 3), color=(255, 0, 0))
    path = tmp_path / "red.png"
    img.save(path, format="PNG")
    return path


@pytest.fixture
def sample_jpeg(tmp_path: Path) -> Path:
    """Create a small 8x6 blue JPEG."""
    img = Image.new("RGB", (8, 6), color=(0, 0, 255))
    path = tmp_path / "blue.jpg"
    img.save(path, format="JPEG")
    return path


@pytest.fixture
def image_dir(tmp_path: Path) -> Path:
    """Create a directory tree with several test images."""
    root = tmp_path / "images"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()

    Image.new("RGB", (10, 10), "red").save(root / "a.png")
    Image.new("RGB", (20, 15), "green").save(root / "b.jpg")
    Image.new("RGB", (5, 5), "blue").save(sub / "c.png")

    # Non-image file (should be ignored)
    (root / "readme.txt").write_text("not an image")

    return root


@pytest.fixture
def sample_mp4(tmp_path: Path) -> Path:
    """A one-second 64x48 MP4 made with ffmpeg (pair with requires_ffmpeg)."""
    import subprocess

    out = tmp_path / "test.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=red:s=64x48:d=1",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert out.exists(), "Failed to create test MP4"
    return out
