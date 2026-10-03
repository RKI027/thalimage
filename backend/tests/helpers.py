"""Seeding helpers shared by the tests.

Scanned data goes through the real scan (`scan_source`); `insert_image`
writes a row directly, for tests that need exact values without files.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from thalimage.core.video import ffmpeg_available

requires_ffmpeg = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not available")


def scan_source(client: TestClient, folder: Path) -> tuple[int, list[str]]:
    """Register `folder` as a source, scan it to the end, and return the
    source id with its image hashes in the default (name) order."""
    source_id = client.post("/api/v1/sources", json={"path": str(folder)}).json()["id"]
    client.post(f"/api/v1/sources/{source_id}/scan")
    # The status stream closes once the scan reaches its terminal phase.
    client.get(f"/api/v1/sources/{source_id}/scan/status")
    items = client.get("/api/v1/images", params={"source_id": source_id}).json()["items"]
    return source_id, [i["content_hash"] for i in items]


def ensure_source(conn: sqlite3.Connection, path: str = "/test") -> int:
    """Return the id of the source at `path`, creating it if needed."""
    conn.execute(
        "INSERT OR IGNORE INTO sources (path, label, recursive) VALUES (?, 'test', 1)", (path,)
    )
    conn.commit()
    return int(conn.execute("SELECT id FROM sources WHERE path = ?", (path,)).fetchone()[0])


def insert_image(
    conn: sqlite3.Connection,
    content_hash: str,
    *,
    source_id: int | None = None,
    filename: str | None = None,
    file_modified: str = "2024-01-01T00:00:00",
    file_created: str | None = None,
    thumb_generated: bool = False,
) -> str:
    """Insert an image and its location as a scan would have, and commit."""
    if source_id is None:
        source_id = ensure_source(conn)
    filename = filename or f"{content_hash}.png"
    conn.execute(
        """INSERT INTO images
           (content_hash, filename, source_id, relative_path,
            file_size, width, height, aspect_ratio, format,
            file_modified, file_created, thumb_generated)
           VALUES (?, ?, ?, ?, 1000, 100, 100, 1.0, 'PNG', ?, ?, ?)""",
        (content_hash, filename, source_id, filename, file_modified, file_created,
         int(thumb_generated)),
    )
    conn.execute(
        """INSERT INTO image_locations
           (source_id, relative_path, content_hash, filename, file_size,
            file_modified, file_created)
           VALUES (?, ?, ?, ?, 1000, ?, ?)""",
        (source_id, filename, content_hash, filename, file_modified, file_created),
    )
    conn.commit()
    return content_hash
