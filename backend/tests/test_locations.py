"""The same content in several places (GEN-006, TST-002, TST-001)."""

import os
import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from tests.helpers import scan_source
from thalimage.db.engine import connect, migrate
from thalimage.services.image_service import resolve_file_path
from thalimage.services.scan_service import run_scan


def _db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "loc.db")
    migrate(conn)
    return conn


def _source(conn: sqlite3.Connection, path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    cur = conn.execute("INSERT INTO sources (path) VALUES (?)", (str(path),))
    conn.commit()
    return int(cur.lastrowid)  # type: ignore[arg-type]


def _only_hash(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT content_hash FROM images").fetchall()
    assert len(rows) == 1
    return str(rows[0][0])


def test_copy_in_two_sources_always_resolves_to_a_real_file(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    sa, sb = _source(conn, a), _source(conn, b)
    Image.new("RGB", (10, 10), "red").save(a / "orig.png")
    shutil.copy(a / "orig.png", b / "favorites-copy.png")
    thumbs = tmp_path / "thumbs"

    for order in ([sa, sb], [sb, sa], [sa, sb, sb, sa]):
        for sid in order:
            run_scan(conn, sid, thumbs)
            h = _only_hash(conn)
            path = resolve_file_path(conn, h)
            assert path is not None and Path(path).is_file(), (order, path)

    # The image keeps one stable primary location across rescans.
    first = conn.execute("SELECT source_id, relative_path FROM images").fetchone()
    run_scan(conn, sb, thumbs)
    run_scan(conn, sa, thumbs)
    assert tuple(conn.execute("SELECT source_id, relative_path FROM images").fetchone()) == tuple(first)
    conn.close()


def test_copy_survives_until_its_last_location_is_gone(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    sa, sb = _source(conn, a), _source(conn, b)
    Image.new("RGB", (10, 10), "red").save(a / "x.png")
    Image.new("RGB", (10, 10), "blue").save(a / "other.png")
    shutil.copy(a / "x.png", b / "x.png")
    Image.new("RGB", (10, 10), "green").save(b / "keep.png")
    thumbs = tmp_path / "thumbs"
    run_scan(conn, sa, thumbs)
    run_scan(conn, sb, thumbs)
    h = conn.execute("SELECT content_hash FROM image_locations WHERE relative_path = 'x.png' LIMIT 1").fetchone()[0]

    # Gone from the primary source: still live, now opened from the other.
    (a / "x.png").unlink()
    run_scan(conn, sa, thumbs)
    row = conn.execute("SELECT source_id, deleted FROM images WHERE content_hash = ?", (h,)).fetchone()
    assert tuple(row) == (sb, 0)
    assert Path(resolve_file_path(conn, h) or "").is_file()

    # Gone everywhere: soft-deleted.
    (b / "x.png").unlink()
    run_scan(conn, sb, thumbs)
    assert conn.execute("SELECT deleted FROM images WHERE content_hash = ?", (h,)).fetchone()[0] == 1
    conn.close()


def test_duplicates_within_a_source_are_not_rehashed(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    a = tmp_path / "a"
    sa = _source(conn, a)
    Image.new("RGB", (10, 10), "red").save(a / "one.png")
    shutil.copy(a / "one.png", a / "two.png")
    thumbs = tmp_path / "thumbs"

    first = run_scan(conn, sa, thumbs)
    second = run_scan(conn, sa, thumbs)

    assert (first.added, first.skipped) == (2, 0)
    assert (second.added, second.skipped) == (0, 2)
    assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM image_locations").fetchone()[0] == 2
    conn.close()


def test_moved_file_keeps_its_image_row(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    a = tmp_path / "a"
    sa = _source(conn, a)
    Image.new("RGB", (10, 10), "red").save(a / "old.png")
    Image.new("RGB", (10, 10), "blue").save(a / "stay.png")
    thumbs = tmp_path / "thumbs"
    run_scan(conn, sa, thumbs)
    h = conn.execute("SELECT content_hash FROM images WHERE relative_path = 'old.png'").fetchone()[0]

    (a / "sub").mkdir()
    os.rename(a / "old.png", a / "sub" / "new.png")
    run_scan(conn, sa, thumbs)

    row = conn.execute(
        "SELECT relative_path, filename, deleted FROM images WHERE content_hash = ?", (h,)
    ).fetchone()
    assert tuple(row) == (str(Path("sub") / "new.png"), "new.png", 0)
    conn.close()


def test_copy_is_listed_under_both_sources(client: TestClient, tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    Image.new("RGB", (10, 10), "red").save(a / "x.png")
    shutil.copy(a / "x.png", b / "x.png")
    Image.new("RGB", (10, 10), "blue").save(b / "y.png")
    sa, ha = scan_source(client, a)
    sb, hb = scan_source(client, b)

    assert set(ha) < set(hb)
    presets = {
        c["source_id"]: c
        for c in client.get("/api/v1/collections", params={"type": "source_preset"}).json()
    }
    assert (presets[sa]["image_count"], presets[sb]["image_count"]) == (1, 2)
    listed = client.get("/api/v1/images", params={"collection_id": presets[sa]["id"]}).json()
    assert [i["content_hash"] for i in listed["items"]] == ha


def test_deleting_one_source_keeps_shared_content_and_its_rankings(
    client: TestClient, db: sqlite3.Connection, tmp_path: Path
) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    Image.new("RGB", (10, 10), "red").save(a / "shared.png")
    Image.new("RGB", (10, 10), "blue").save(a / "only-a.png")
    shutil.copy(a / "shared.png", b / "shared.png")
    Image.new("RGB", (10, 10), "green").save(b / "only-b.png")
    sa, _ = scan_source(client, a)
    sb, hb = scan_source(client, b)
    shared = next(
        h for h in hb
        if db.execute(
            "SELECT COUNT(*) FROM image_locations WHERE content_hash = ?", (h,)
        ).fetchone()[0] == 2
    )
    coll = client.post("/api/v1/collections", json={"name": "c"}).json()["id"]
    client.post(f"/api/v1/collections/{coll}/images", json={"hashes": hb})
    other = next(h for h in hb if h != shared)
    client.post(
        f"/api/v1/collections/{coll}/elo/vote",
        json={"winner_hash": shared, "loser_hash": other},
    )

    assert client.delete(f"/api/v1/sources/{sa}").status_code == 204

    row = db.execute(
        "SELECT source_id, deleted FROM images WHERE content_hash = ?", (shared,)
    ).fetchone()
    assert tuple(row) == (sb, 0)
    assert db.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM image_locations WHERE source_id = ?", (sa,)).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM elo_scores WHERE content_hash = ? AND collection_id = ?",
        (shared, coll),
    ).fetchone()[0] == 1
    assert client.get(f"/api/v1/images/{shared}/file").status_code == 200
