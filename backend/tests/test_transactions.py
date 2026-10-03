"""A failed write must not leave the database locked (GEN-002)."""

import sqlite3

from fastapi.testclient import TestClient


def _assert_writable(db: sqlite3.Connection) -> None:
    """Another connection can take the write lock at once, without waiting."""
    db.execute("PRAGMA busy_timeout = 0")
    db.execute("INSERT INTO settings (key, value) VALUES ('probe', 'x')")
    db.rollback()


def test_conflicting_tag_create_releases_the_write_lock(
    client: TestClient, db: sqlite3.Connection
) -> None:
    assert client.post("/api/v1/tags", json={"name": "dup"}).status_code == 201
    assert client.post("/api/v1/tags", json={"name": "dup"}).status_code == 409
    _assert_writable(db)


def test_conflicting_source_create_releases_the_write_lock(
    client: TestClient, db: sqlite3.Connection, tmp_path
) -> None:
    folder = tmp_path / "pics"
    folder.mkdir()
    assert client.post("/api/v1/sources", json={"path": str(folder)}).status_code == 201
    assert client.post("/api/v1/sources", json={"path": str(folder)}).status_code == 409
    _assert_writable(db)


def test_failed_collection_insert_rolls_back(
    client: TestClient, db: sqlite3.Connection
) -> None:
    coll = client.post("/api/v1/collections", json={"name": "c"}).json()
    resp = client.post(
        f"/api/v1/collections/{coll['id']}/images", json={"hashes": ["f" * 64]}
    )
    assert resp.status_code == 200
    assert resp.json() == {"added": 0}
    _assert_writable(db)
    assert db.execute("SELECT COUNT(*) FROM collection_images").fetchone()[0] == 0


def test_request_connection_rolls_back_what_the_handler_left_open(tmp_path) -> None:
    """Whatever a handler leaves uncommitted is rolled back when the request
    ends, so the next writer is not blocked and the partial work is gone."""
    from thalimage.db.engine import connect, migrate
    from thalimage.deps import open_db

    path = tmp_path / "t.db"
    other = connect(path)
    migrate(other)

    gen = open_db(path)
    conn = next(gen)
    conn.execute("INSERT INTO settings (key, value) VALUES ('half', 'done')")
    try:
        conn.execute("INSERT INTO collection_images (collection_id, content_hash) VALUES (99, 'x')")
    except sqlite3.IntegrityError:
        pass
    gen.close()

    _assert_writable(other)
    assert other.execute("SELECT COUNT(*) FROM settings WHERE key = 'half'").fetchone()[0] == 0
    other.close()


def test_adding_images_to_a_source_preset_is_rejected(
    client: TestClient, db: sqlite3.Connection, tmp_path
) -> None:
    folder = tmp_path / "pics"
    folder.mkdir()
    client.post("/api/v1/sources", json={"path": str(folder)})
    preset = client.get("/api/v1/collections", params={"type": "source_preset"}).json()[0]
    resp = client.post(
        f"/api/v1/collections/{preset['id']}/images", json={"hashes": ["f" * 64]}
    )
    assert resp.status_code == 400
    _assert_writable(db)
