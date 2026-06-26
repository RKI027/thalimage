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


def _split_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    Uses sqlite3.complete_statement() to detect statement boundaries, so
    triggers (whose BEGIN...END bodies contain semicolons) are handled correctly.
    Comments and blank lines are ignored.
    """
    statements: list[str] = []
    current: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()
        # Skip pure-comment and blank lines when accumulating, but keep them
        # inside a partially-built statement for correct parsing.
        if not current and (not stripped or stripped.startswith("--")):
            continue
        current.append(line)
        candidate = "\n".join(current)
        if sqlite3.complete_statement(candidate):
            stmt = candidate.strip()
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


def migrate(conn: sqlite3.Connection) -> int:
    """Run all pending migrations and return the new schema version.

    Migrations are SQL files in the migrations/ directory named NNN_description.sql.
    Each migration runs inside a transaction: either all statements succeed and the
    schema version advances, or the transaction rolls back and the version is unchanged.

    ALTER TABLE ADD COLUMN failures caused by an already-present column (from a
    previous partial run) are silently skipped so the migration can complete cleanly.
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
        statements = _split_statements(sql)

        # Run the entire migration + version update atomically.
        # executescript() issues an implicit COMMIT first, so we wrap the whole
        # thing in BEGIN/COMMIT to get a real transaction.
        conn.executescript(
            "BEGIN;\n"
            + _statements_to_script(statements, conn)
            + f"INSERT INTO schema_version (version) VALUES ({migration_version});\n"
            "COMMIT;"
        )
        version = migration_version

    return version


def _statements_to_script(statements: list[str], conn: sqlite3.Connection) -> str:
    """Return statements as a SQL script, omitting ALTER TABLE ADD COLUMN
    statements for columns that already exist in the database."""
    lines: list[str] = []
    for stmt in statements:
        upper = stmt.upper().split()
        if (
            len(upper) >= 5
            and upper[0] == "ALTER"
            and upper[1] == "TABLE"
            and upper[3] in ("ADD", "ADD")
            and "COLUMN" in upper[3:6]
        ):
            # Extract table name and column name to check existence
            table, col = _parse_add_column(stmt)
            if table and col:
                exists = conn.execute(
                    "SELECT 1 FROM pragma_table_info(?) WHERE name = ?",
                    (table, col),
                ).fetchone()
                if exists:
                    continue  # Column already present; skip to avoid error
        lines.append(stmt + ("" if stmt.rstrip().endswith(";") else ";"))
        lines.append("\n")
    return "".join(lines)


def _parse_add_column(stmt: str) -> tuple[str, str] | tuple[None, None]:
    """Extract (table_name, column_name) from ALTER TABLE t ADD [COLUMN] c ...
    Returns (None, None) if the statement cannot be parsed."""
    import re
    m = re.match(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+(?:COLUMN\s+)?(\w+)",
        stmt.strip(),
        re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)
    return None, None
