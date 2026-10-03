"""Collection CRUD service."""

import sqlite3
from typing import Optional

from pydantic import BaseModel


class Collection(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    type: str = "manual"
    source_id: Optional[int] = None
    sort_by: str = "name"
    sort_dir: str = "asc"
    nsfw: bool = False
    created_at: str
    updated_at: str
    image_count: int = 0


_COUNT_SQL = """
    SELECT c.*,
        CASE WHEN c.type = 'source_preset'
            THEN (SELECT COUNT(*) FROM images WHERE source_id = c.source_id AND deleted = 0)
            ELSE COUNT(ci.content_hash)
        END AS image_count
    FROM collections c
    LEFT JOIN collection_images ci ON c.id = ci.collection_id
"""


def list_collections(
    conn: sqlite3.Connection,
    *,
    type: Optional[str] = None,
) -> list[Collection]:
    """List all collections with image counts, optionally filtered by type."""
    if type is not None:
        rows = conn.execute(
            _COUNT_SQL + " WHERE c.type = ? GROUP BY c.id ORDER BY c.name",
            (type,),
        ).fetchall()
    else:
        rows = conn.execute(
            _COUNT_SQL + " GROUP BY c.id ORDER BY c.name"
        ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection(conn: sqlite3.Connection, collection_id: int) -> Optional[Collection]:
    row = conn.execute(
        _COUNT_SQL + " WHERE c.id = ? GROUP BY c.id",
        (collection_id,),
    ).fetchone()
    if row is None:
        return None
    return Collection(**dict(row))


def create_collection(
    conn: sqlite3.Connection,
    name: str,
    parent_id: Optional[int] = None,
) -> Collection:
    cursor = conn.execute(
        "INSERT INTO collections (name, parent_id) VALUES (?, ?)",
        (name, parent_id),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    result = get_collection(conn, cursor.lastrowid)
    assert result is not None
    return result


def update_collection(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    name: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    nsfw: Optional[bool] = None,
) -> Optional[Collection] | str:
    """Update a collection. Returns error string if preset rename attempted."""
    coll = get_collection(conn, collection_id)
    if coll is None:
        return None
    if name is not None and coll.type != "manual":
        return "preset_rename_forbidden"

    updates = []
    params: list[object] = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if sort_by is not None:
        updates.append("sort_by = ?")
        params.append(sort_by)
    if sort_dir is not None:
        updates.append("sort_dir = ?")
        params.append(sort_dir)
    if nsfw is not None:
        updates.append("nsfw = ?")
        params.append(1 if nsfw else 0)

    if not updates:
        return get_collection(conn, collection_id)

    updates.append("updated_at = datetime('now')")
    params.append(collection_id)
    conn.execute(
        f"UPDATE collections SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    return get_collection(conn, collection_id)


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> bool | str:
    """Delete a collection. Returns error string if preset deletion attempted."""
    coll = get_collection(conn, collection_id)
    if coll is None:
        return False
    if coll.type != "manual":
        return "preset_delete_forbidden"
    deleted = purge_collection(conn, collection_id)
    conn.commit()
    return deleted


def purge_collection(conn: sqlite3.Connection, collection_id: int) -> bool:
    """Delete a collection and the rows that reference it, without committing.

    votes and elo_scores reference collections with no ON DELETE action, so
    they go first; child collections move up to the deleted one's parent.
    collection_images cascades. Returns False if there was no such row.
    """
    conn.execute("DELETE FROM votes WHERE collection_id = ?", (collection_id,))
    conn.execute("DELETE FROM elo_scores WHERE collection_id = ?", (collection_id,))
    conn.execute(
        "UPDATE collections SET parent_id ="
        " (SELECT parent_id FROM collections WHERE id = ?) WHERE parent_id = ?",
        (collection_id, collection_id),
    )
    cursor = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    return cursor.rowcount > 0


def add_images(
    conn: sqlite3.Connection,
    collection_id: int,
    hashes: list[str],
) -> int:
    """Add images to a collection. Returns the number of rows actually inserted
    (duplicates and unknown hashes don't count). OR IGNORE does not cover
    foreign-key failures, so unknown hashes are filtered out by the SELECT."""
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO collection_images (collection_id, content_hash)"
        " SELECT ?, content_hash FROM images WHERE content_hash = ?",
        [(collection_id, h) for h in hashes],
    )
    conn.commit()
    return conn.total_changes - before


def remove_images(
    conn: sqlite3.Connection,
    collection_id: int,
    hashes: list[str],
) -> int:
    """Remove images from a collection. Returns number removed."""
    if not hashes:
        return 0
    placeholders = ",".join("?" * len(hashes))
    cursor = conn.execute(
        f"DELETE FROM collection_images WHERE collection_id = ? AND content_hash IN ({placeholders})",
        [collection_id, *hashes],
    )
    conn.commit()
    return cursor.rowcount


def get_or_create_source_preset(
    conn: sqlite3.Connection,
    source_id: int,
    name: str,
) -> Collection:
    """Get or create a source preset collection."""
    row = conn.execute(
        "SELECT id FROM collections WHERE source_id = ? AND type = 'source_preset'",
        (source_id,),
    ).fetchone()
    if row is not None:
        result = get_collection(conn, row["id"])
        assert result is not None
        return result

    cursor = conn.execute(
        "INSERT INTO collections (name, type, source_id) VALUES (?, 'source_preset', ?)",
        (name, source_id),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    result = get_collection(conn, cursor.lastrowid)
    assert result is not None
    return result


