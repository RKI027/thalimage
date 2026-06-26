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
    archived: bool = False
    nsfw: bool = False


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

# Video formats as stored in the format column (file extension, uppercase)
VIDEO_FORMATS = {"MP4", "MOV", "WEBM", "AVI"}

ASPECT_RATIO_FILTERS: dict[str, tuple[str, list[object]]] = {
    "portrait": ("aspect_ratio < 0.9", []),
    "square": ("aspect_ratio BETWEEN 0.9 AND 1.1", []),
    "landscape": ("aspect_ratio BETWEEN 1.1 AND 2.0", []),
    "wide": ("aspect_ratio > 2.0", []),
}


def append_media_filters(
    q: str,
    params: list[object],
    *,
    prefix: str = "",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    aspect_ratio_filter: Optional[str] = None,
    media_type: Optional[str] = None,
) -> tuple[str, list[object]]:
    """Append the date / aspect-ratio / media-type WHERE clauses shared by the
    image listing and ELO pair queries. `prefix` qualifies column references
    (e.g. "i." when the images table is aliased)."""
    if date_from is not None:
        q += f" AND {prefix}file_modified >= ?"
        params.append(date_from)
    if date_to is not None:
        q += f" AND {prefix}file_modified <= ?"
        params.append(date_to)
    if aspect_ratio_filter in ASPECT_RATIO_FILTERS:
        clause, _ = ASPECT_RATIO_FILTERS[aspect_ratio_filter]
        q += f" AND {prefix}{clause}"
    if media_type in ("video", "image"):
        placeholders = ",".join("?" * len(VIDEO_FORMATS))
        op = "IN" if media_type == "video" else "NOT IN"
        q += f" AND {prefix}format {op} ({placeholders})"
        params.extend(VIDEO_FORMATS)
    return q, params


def list_images(
    conn: sqlite3.Connection,
    *,
    cursor: Optional[str] = None,
    limit: int = 200,
    sort: str = "name",
    direction: str = "asc",
    source_id: Optional[int] = None,
    collection_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    aspect_ratio_filter: Optional[str] = None,
    media_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    show_nsfw: bool = False,
) -> ImagePage:
    """Cursor-paginated image listing."""
    col = SORT_COLUMNS.get(sort, "filename")
    if direction not in ("asc", "desc"):
        direction = "asc"

    def _apply_filters(q: str, p: list[object]) -> tuple[str, list[object]]:
        """Append WHERE clauses for optional filters."""
        if source_id is not None:
            q += " AND source_id = ?"
            p.append(source_id)
        if collection_id is not None:
            q += " AND content_hash IN (SELECT content_hash FROM collection_images WHERE collection_id = ?)"
            p.append(collection_id)
        q, _ = append_media_filters(
            q, p,
            date_from=date_from,
            date_to=date_to,
            aspect_ratio_filter=aspect_ratio_filter,
            media_type=media_type,
        )
        if tags:
            for tag_name in tags:
                q += (
                    " AND EXISTS ("
                    "SELECT 1 FROM image_tags it JOIN tags t ON t.id = it.tag_id"
                    " WHERE it.image_hash = content_hash AND t.name = ?"
                    ")"
                )
                p.append(tag_name)
        if not show_nsfw:
            q += (
                " AND nsfw = 0"
                " AND content_hash NOT IN ("
                "SELECT ci.content_hash FROM collection_images ci"
                " JOIN collections c ON c.id = ci.collection_id WHERE c.nsfw = 1)"
            )
        return q, p

    # Total count
    count_sql, count_params = _apply_filters(
        "SELECT COUNT(*) FROM images WHERE deleted = 0 AND archived = 0", []
    )
    total = conn.execute(count_sql, count_params).fetchone()[0]

    # Query. Select the active sort column too (when it isn't already a summary
    # field) so the cursor can carry its real value; extra columns are ignored
    # when building ImageSummary.
    select_cols = [
        "content_hash", "filename", "source_id", "relative_path", "width", "height",
        "aspect_ratio", "format", "thumb_generated", "archived", "nsfw",
    ]
    if col not in select_cols:
        select_cols.append(col)
    sql, params = _apply_filters(
        f"SELECT {', '.join(select_cols)} FROM images WHERE deleted = 0 AND archived = 0",
        [],
    )

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

    items = [ImageSummary(**{k: r[k] for k in ImageSummary.model_fields}) for r in rows]

    next_cursor = None
    if has_next and rows:
        last_row = rows[-1]
        next_cursor = f"{last_row[col]}|{last_row['content_hash']}"

    return ImagePage(items=items, next_cursor=next_cursor, total_count=total)


def get_image(conn: sqlite3.Connection, content_hash: str) -> Optional[ImageDetail]:
    """Get full image details including metadata. Returns archived images too."""
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


def set_archived(
    conn: sqlite3.Connection,
    content_hash: str,
    archived: bool,
) -> bool:
    """Set archived state on an image. Returns False if image not found."""
    cursor = conn.execute(
        "UPDATE images SET archived = ? WHERE content_hash = ? AND deleted = 0",
        (1 if archived else 0, content_hash),
    )
    conn.commit()
    return cursor.rowcount > 0


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
