"""Tag CRUD and image tagging service."""

import sqlite3
from typing import Optional

from pydantic import BaseModel


class Tag(BaseModel):
    id: int
    name: str
    nsfw: bool
    created_at: str


def list_tags(conn: sqlite3.Connection, *, search: Optional[str] = None) -> list[Tag]:
    """List all tags, optionally filtering by a case-insensitive name substring."""
    if search is not None:
        rows = conn.execute(
            "SELECT id, name, nsfw, created_at FROM tags WHERE name LIKE ? ORDER BY name",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, nsfw, created_at FROM tags ORDER BY name"
        ).fetchall()
    return [Tag(**dict(r)) for r in rows]


def get_tag(conn: sqlite3.Connection, tag_id: int) -> Optional[Tag]:
    """Fetch a single tag by id. Returns None if not found."""
    row = conn.execute(
        "SELECT id, name, nsfw, created_at FROM tags WHERE id = ?", (tag_id,)
    ).fetchone()
    return Tag(**dict(row)) if row else None


def create_tag(
    conn: sqlite3.Connection, name: str, *, nsfw: bool = False
) -> Tag:
    """Create a new tag. Raises on duplicate name."""
    cursor = conn.execute(
        "INSERT INTO tags (name, nsfw) VALUES (?, ?)", (name, 1 if nsfw else 0)
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, name, nsfw, created_at FROM tags WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return Tag(**dict(row))


def update_tag(
    conn: sqlite3.Connection,
    tag_id: int,
    *,
    name: Optional[str] = None,
    nsfw: Optional[bool] = None,
) -> Optional[Tag]:
    """Update a tag's name and/or nsfw flag. Returns None if not found."""
    if get_tag(conn, tag_id) is None:
        return None
    if name is not None:
        conn.execute("UPDATE tags SET name = ? WHERE id = ?", (name, tag_id))
    if nsfw is not None:
        conn.execute("UPDATE tags SET nsfw = ? WHERE id = ?", (1 if nsfw else 0, tag_id))
    conn.commit()
    return get_tag(conn, tag_id)


def delete_tag(conn: sqlite3.Connection, tag_id: int) -> bool:
    """Delete a tag (cascades to image_tags). Returns False if not found."""
    cursor = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_image_tags(conn: sqlite3.Connection, image_hash: str) -> list[Tag]:
    """Return all tags attached to an image."""
    rows = conn.execute(
        """SELECT t.id, t.name, t.nsfw, t.created_at
           FROM image_tags it
           JOIN tags t ON t.id = it.tag_id
           WHERE it.image_hash = ?
           ORDER BY t.name""",
        (image_hash,),
    ).fetchall()
    return [Tag(**dict(r)) for r in rows]


def add_image_tag(
    conn: sqlite3.Connection,
    image_hash: str,
    tag_id: int,
    *,
    created_by: Optional[str] = None,
) -> None:
    """Attach a tag to an image. Idempotent: silently ignores duplicates."""
    conn.execute(
        """INSERT OR IGNORE INTO image_tags (image_hash, tag_id, created_by)
           VALUES (?, ?, ?)""",
        (image_hash, tag_id, created_by),
    )
    conn.commit()


def remove_image_tag(
    conn: sqlite3.Connection, image_hash: str, tag_id: int
) -> bool:
    """Remove a tag from an image. Returns False if the association didn't exist."""
    cursor = conn.execute(
        "DELETE FROM image_tags WHERE image_hash = ? AND tag_id = ?",
        (image_hash, tag_id),
    )
    conn.commit()
    return cursor.rowcount > 0
