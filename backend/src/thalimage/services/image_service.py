"""Image retrieval and query service."""

import sqlite3
from typing import Optional

from pydantic import BaseModel


class ImageSummary(BaseModel):
    content_hash: str
    filename: str
    source_id: int
    relative_path: str
    width: int
    height: int
    aspect_ratio: float
    format: str
    thumb_generated: bool


class ImageDetail(ImageSummary):
    file_size: int
    file_modified: str
    file_created: Optional[str]
    ai_tool: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    raw_params: Optional[str] = None
    exif_data: Optional[str] = None
    png_text: Optional[str] = None


class ImagePage(BaseModel):
    items: list[ImageSummary]
    next_cursor: Optional[str] = None
    total_count: int


SORT_COLUMNS = {
    "name": "filename",
    "date_modified": "file_modified",
    "date_created": "file_created",
    "size": "file_size",
    "aspect_ratio": "aspect_ratio",
}


def list_images(
    conn: sqlite3.Connection,
    *,
    cursor: Optional[str] = None,
    limit: int = 200,
    sort: str = "name",
    direction: str = "asc",
    source_id: Optional[int] = None,
    collection_id: Optional[int] = None,
) -> ImagePage:
    """Cursor-paginated image listing."""
    col = SORT_COLUMNS.get(sort, "filename")
    if direction not in ("asc", "desc"):
        direction = "asc"

    # Total count
    count_sql = "SELECT COUNT(*) FROM images WHERE deleted = 0"
    count_params: list[object] = []
    if source_id is not None:
        count_sql += " AND source_id = ?"
        count_params.append(source_id)
    if collection_id is not None:
        count_sql += " AND content_hash IN (SELECT content_hash FROM collection_images WHERE collection_id = ?)"
        count_params.append(collection_id)

    total = conn.execute(count_sql, count_params).fetchone()[0]

    # Query
    sql = "SELECT content_hash, filename, source_id, relative_path, width, height, aspect_ratio, format, thumb_generated FROM images WHERE deleted = 0"
    params: list[object] = []

    if source_id is not None:
        sql += " AND source_id = ?"
        params.append(source_id)
    if collection_id is not None:
        sql += " AND content_hash IN (SELECT content_hash FROM collection_images WHERE collection_id = ?)"
        params.append(collection_id)

    if cursor is not None:
        op = ">" if direction == "asc" else "<"
        sql += f" AND ({col}, content_hash) {op} (?, ?)"
        # cursor encodes "sort_value|hash"
        parts = cursor.split("|", 1)
        params.extend(parts)

    sql += f" ORDER BY {col} {direction}, content_hash {direction}"
    sql += " LIMIT ?"
    params.append(limit + 1)  # fetch one extra to detect next page

    rows = conn.execute(sql, params).fetchall()

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    items = [ImageSummary(**dict(r)) for r in rows]

    next_cursor = None
    if has_next and items:
        last = items[-1]
        last_sort_val = getattr(last, sort if sort != "name" else "filename", last.filename)
        next_cursor = f"{last_sort_val}|{last.content_hash}"

    return ImagePage(items=items, next_cursor=next_cursor, total_count=total)


def get_image(conn: sqlite3.Connection, content_hash: str) -> Optional[ImageDetail]:
    """Get full image details including metadata."""
    row = conn.execute(
        """SELECT i.*, m.ai_tool, m.prompt, m.negative_prompt,
                  m.raw_params, m.exif_data, m.png_text
           FROM images i
           LEFT JOIN image_metadata m ON i.content_hash = m.content_hash
           WHERE i.content_hash = ? AND i.deleted = 0""",
        (content_hash,),
    ).fetchone()

    if row is None:
        return None

    return ImageDetail(**dict(row))


def resolve_file_path(
    conn: sqlite3.Connection, content_hash: str
) -> Optional[str]:
    """Resolve the full file path for an image."""
    row = conn.execute(
        """SELECT s.path, i.relative_path
           FROM images i JOIN sources s ON i.source_id = s.id
           WHERE i.content_hash = ? AND i.deleted = 0""",
        (content_hash,),
    ).fetchone()

    if row is None:
        return None

    from pathlib import Path
    return str(Path(row["path"]) / row["relative_path"])
