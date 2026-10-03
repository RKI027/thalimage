"""Data-changing migrations, run against databases that hold data (TST-006).

Each test migrates to the version before the one under test, inserts rows
the way that older schema allowed, then migrates the rest of the way.
"""

import sqlite3
from pathlib import Path

from thalimage.db.engine import connect, migrate


def _db_at(tmp_path: Path, version: int) -> sqlite3.Connection:
    conn = connect(tmp_path / "m.db")
    assert migrate(conn, target=version) == version
    return conn


def _image(conn: sqlite3.Connection, h: str, source_id: int = 1) -> None:
    conn.execute(
        """INSERT INTO images (content_hash, filename, source_id, relative_path,
               file_size, width, height, aspect_ratio, format, file_modified)
           VALUES (?, ?, ?, ?, 1, 1, 1, 1.0, 'PNG', '2024-01-01')""",
        (h, h, source_id, h),
    )


def _hashes(conn: sqlite3.Connection, sql: str, *params: object) -> set[str]:
    return {r[0] for r in conn.execute(sql, params)}


def test_migrate_stops_at_target(tmp_path: Path) -> None:
    conn = _db_at(tmp_path, 2)
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 2
    assert migrate(conn) > 2


def test_003_drops_preset_snapshots_and_keeps_manual_rows(tmp_path: Path) -> None:
    conn = _db_at(tmp_path, 2)
    conn.execute("INSERT INTO sources (id, path) VALUES (1, '/a')")
    for h in ("x", "y"):
        _image(conn, h)
    conn.execute("INSERT INTO collections (id, name) VALUES (1, 'manual')")
    conn.execute(
        "INSERT INTO collections (id, name, type, source_id) VALUES (2, 'a', 'source_preset', 1)"
    )
    conn.executemany(
        "INSERT INTO collection_images (collection_id, content_hash) VALUES (?, ?)",
        [(1, "x"), (2, "x"), (2, "y")],
    )
    conn.commit()

    migrate(conn, target=3)

    rows = {tuple(r) for r in conn.execute("SELECT collection_id, content_hash FROM collection_images")}
    assert rows == {(1, "x")}
    assert conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 2
    conn.close()


def test_009_flags_follow_the_nsfw_tag_name_not_the_column(tmp_path: Path) -> None:
    conn = _db_at(tmp_path, 8)
    conn.execute("INSERT INTO sources (id, path) VALUES (1, '/a')")
    for h in ("lower", "upper", "column_only", "plain"):
        _image(conn, h)
    conn.executemany(
        "INSERT INTO tags (id, name, nsfw) VALUES (?, ?, ?)",
        [(1, "nsfw", 0), (2, "NSFW", 0), (3, "spicy", 1), (4, "cat", 0)],
    )
    # Under 007's triggers, tag 3 (nsfw column = 1) flags its image.
    conn.executemany(
        "INSERT INTO image_tags (image_hash, tag_id) VALUES (?, ?)",
        [("lower", 1), ("upper", 2), ("column_only", 3), ("plain", 4)],
    )
    conn.commit()
    assert _hashes(conn, "SELECT content_hash FROM images WHERE nsfw = 1") == {"column_only"}

    migrate(conn, target=9)

    assert _hashes(conn, "SELECT content_hash FROM images WHERE nsfw = 1") == {"lower", "upper"}
    # The new triggers go by name from here on.
    _image(conn, "later")
    conn.execute("INSERT INTO image_tags (image_hash, tag_id) VALUES ('later', 2)")
    conn.execute("DELETE FROM image_tags WHERE image_hash = 'lower'")
    assert _hashes(conn, "SELECT content_hash FROM images WHERE nsfw = 1") == {"upper", "later"}
    conn.close()


def test_010_unsticks_images_flagged_by_a_deleted_nsfw_tag(tmp_path: Path) -> None:
    conn = _db_at(tmp_path, 9)
    conn.execute("INSERT INTO sources (id, path) VALUES (1, '/a')")
    for h in ("stuck", "tagged"):
        _image(conn, h)
    conn.execute("INSERT INTO tags (id, name) VALUES (1, 'nsfw'), (2, 'NSFW')")
    conn.execute(
        "INSERT INTO image_tags (image_hash, tag_id) VALUES ('stuck', 1), ('tagged', 2)"
    )
    # Before 010, deleting the tag cascaded past the triggers: the flag stuck.
    conn.execute("DELETE FROM tags WHERE id = 1")
    conn.commit()
    assert _hashes(conn, "SELECT content_hash FROM images WHERE nsfw = 1") == {"stuck", "tagged"}

    migrate(conn, target=10)

    assert _hashes(conn, "SELECT content_hash FROM images WHERE nsfw = 1") == {"tagged"}
    conn.close()
