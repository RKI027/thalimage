"""Tests for database engine and migrations."""

from pathlib import Path

from thalimage.db.engine import connect, current_version, migrate


def test_connect_enables_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    conn.close()


def test_connect_enables_foreign_keys(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()


def test_connect_row_factory(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'hello')")
    row = conn.execute("SELECT * FROM t").fetchone()
    assert row["a"] == 1
    assert row["b"] == "hello"
    conn.close()


def test_current_version_no_migrations(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    assert current_version(conn) == 0
    conn.close()


def test_migrate_runs_initial(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    version = migrate(conn)
    assert version >= 1

    # Verify tables exist
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    expected = {"sources", "images", "image_metadata", "collections",
                "collection_images", "votes", "elo_scores", "schema_version"}
    assert expected.issubset(tables)
    conn.close()


def test_migrate_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    v1 = migrate(conn)
    v2 = migrate(conn)
    assert v1 == v2
    conn.close()


def test_current_version_after_migrate(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    assert current_version(conn) == 1
    conn.close()
