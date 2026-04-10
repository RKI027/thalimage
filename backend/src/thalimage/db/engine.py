"""SQLite database connection and migration runner."""

import sqlite3
from importlib import resources
from pathlib import Path


def connect(db_path: Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path), check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version, or 0 if no migrations have run."""
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0


def migrate(conn: sqlite3.Connection) -> int:
    """Run all pending migrations and return the new schema version.

    Migrations are SQL files in the migrations/ directory named NNN_description.sql.
    Each migration runs inside a transaction.
    """
    migrations_dir = resources.files("thalimage.db") / "migrations"
    migration_files = sorted(
        (
            p for p in migrations_dir.iterdir()  # type: ignore[union-attr]
            if p.name.endswith(".sql")  # type: ignore[union-attr]
        ),
        key=lambda p: p.name,  # type: ignore[union-attr]
    )

    version = current_version(conn)

    for migration_path in migration_files:
        migration_version = int(migration_path.name.split("_")[0])  # type: ignore[union-attr]
        if migration_version <= version:
            continue

        sql = migration_path.read_text()  # type: ignore[union-attr]
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (migration_version,),
        )
        conn.commit()
        version = migration_version

    return version
