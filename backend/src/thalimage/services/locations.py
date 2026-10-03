"""Keep each image's primary location in step with image_locations."""

import sqlite3
from collections.abc import Iterable
from pathlib import Path

# Rows of image_locations holding a given hash, the image's current primary
# location first, then by source and path so the choice is stable.
_LOCATIONS = """
    SELECT l.source_id, l.relative_path, l.filename,
           l.file_size, l.file_modified, l.file_created
    FROM image_locations l JOIN images i ON i.content_hash = l.content_hash
    WHERE l.content_hash = ?
    ORDER BY (l.source_id = i.source_id AND l.relative_path = i.relative_path) DESC,
             l.source_id, l.relative_path
"""


def in_source_sql(source_param: str = "?", hash_col: str = "content_hash") -> str:
    """SQL condition: the image has a location in the given source."""
    return (
        f"{hash_col} IN (SELECT content_hash FROM image_locations"
        f" WHERE source_id = {source_param})"
    )


def sync_images(conn: sqlite3.Connection, hashes: Iterable[str]) -> None:
    """Point each image at a location that still exists, or mark it deleted.

    Runs inside the caller's transaction; does not commit.
    """
    for h in set(hashes):
        loc = conn.execute(_LOCATIONS, (h,)).fetchone()
        if loc is None:
            conn.execute("UPDATE images SET deleted = 1 WHERE content_hash = ?", (h,))
            continue
        conn.execute(
            """UPDATE images SET source_id = ?, relative_path = ?, filename = ?,
                   file_size = ?, file_modified = ?, file_created = ?, deleted = 0
               WHERE content_hash = ?""",
            (loc["source_id"], loc["relative_path"], loc["filename"], loc["file_size"],
             loc["file_modified"], loc["file_created"], h),
        )


def resolve_paths(conn: sqlite3.Connection, content_hash: str) -> list[str]:
    """Absolute paths of a live image's locations, primary first."""
    rows = conn.execute(
        """SELECT s.path, l.relative_path
           FROM image_locations l
           JOIN images i ON i.content_hash = l.content_hash
           JOIN sources s ON s.id = l.source_id
           WHERE l.content_hash = ? AND i.deleted = 0
           ORDER BY (l.source_id = i.source_id AND l.relative_path = i.relative_path) DESC,
                    l.source_id, l.relative_path""",
        (content_hash,),
    ).fetchall()
    return [str(Path(r["path"]) / r["relative_path"]) for r in rows]
