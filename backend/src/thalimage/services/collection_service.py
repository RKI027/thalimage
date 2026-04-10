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
    created_at: str
    updated_at: str
    image_count: int = 0


def list_collections(
    conn: sqlite3.Connection,
    *,
    type: Optional[str] = None,
) -> list[Collection]:
    """List all collections with image counts, optionally filtered by type."""
    if type is not None:
        rows = conn.execute(
            """SELECT c.*, COUNT(ci.content_hash) as image_count
               FROM collections c
               LEFT JOIN collection_images ci ON c.id = ci.collection_id
               WHERE c.type = ?
               GROUP BY c.id
               ORDER BY c.name""",
            (type,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT c.*, COUNT(ci.content_hash) as image_count
               FROM collections c
               LEFT JOIN collection_images ci ON c.id = ci.collection_id
               GROUP BY c.id
               ORDER BY c.name"""
        ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection(conn: sqlite3.Connection, collection_id: int) -> Optional[Collection]:
    row = conn.execute(
        """SELECT c.*, COUNT(ci.content_hash) as image_count
           FROM collections c
           LEFT JOIN collection_images ci ON c.id = ci.collection_id
           WHERE c.id = ?
           GROUP BY c.id""",
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
    return get_collection(conn, cursor.lastrowid)  # type: ignore[return-value]


def update_collection(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    name: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
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
    cursor = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    conn.commit()
    return cursor.rowcount > 0


def add_images(
    conn: sqlite3.Connection,
    collection_id: int,
    hashes: list[str],
) -> int:
    """Add images to a collection. Returns number added."""
    added = 0
    for h in hashes:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO collection_images (collection_id, content_hash) VALUES (?, ?)",
                (collection_id, h),
            )
            added += 1
        except Exception:
            pass
    conn.commit()
    return added


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
        return get_collection(conn, row["id"])  # type: ignore[return-value]

    cursor = conn.execute(
        "INSERT INTO collections (name, type, source_id) VALUES (?, 'source_preset', ?)",
        (name, source_id),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return get_collection(conn, cursor.lastrowid)  # type: ignore[return-value]


def sync_source_preset_images(
    conn: sqlite3.Connection,
    collection_id: int,
    source_id: int,
) -> None:
    """Replace a source preset's images with all non-deleted images from its source."""
    conn.execute(
        "DELETE FROM collection_images WHERE collection_id = ?",
        (collection_id,),
    )
    conn.execute(
        """INSERT INTO collection_images (collection_id, content_hash)
           SELECT ?, content_hash FROM images
           WHERE source_id = ? AND deleted = 0""",
        (collection_id, source_id),
    )
    conn.commit()
