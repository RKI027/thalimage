"""Shared test fixtures."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from thalimage.app import create_app
from thalimage.deps import get_db, get_thumb_dir
from thalimage.db.engine import connect, migrate


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

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_thumb_dir] = lambda: thumb_dir

    with TestClient(app) as c:
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
