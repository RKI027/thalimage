"""Image retrieval and query service."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from thalimage.core.video import VIDEO_EXTENSIONS
from thalimage.services.elo_ranking import EloCut, in_cut_sql
from thalimage.services.folders import (
    folder_tags,
    in_folder_params,
    in_folder_sql,
    tagged_folder,
)
from thalimage.services.locations import in_source_sql, resolve_paths


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


# The images columns an ImageSummary is built from, in one place.
SUMMARY_COLUMNS: tuple[str, ...] = tuple(ImageSummary.model_fields)


def summary_columns_sql(alias: str = "") -> str:
    """The summary columns as a SELECT list, optionally qualified ("i.")."""
    return ", ".join(f"{alias}{c}" for c in SUMMARY_COLUMNS)


def summary_from_row(row: sqlite3.Row) -> ImageSummary:
    """Build an ImageSummary from a row that selected SUMMARY_COLUMNS
    (extra columns are ignored)."""
    return ImageSummary(**{c: row[c] for c in SUMMARY_COLUMNS})


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
    folder_tags: list[str] = []
    # Other files of this image with a different tool, prompt or negative prompt.
    other_versions: int = 0


class InvalidCursor(ValueError):
    """A pagination cursor that this listing could not have produced."""


def _parse_cursor(cursor: str, *, numeric: bool) -> tuple[object, str]:
    """Split a "sort_value|hash" cursor. The hash never contains "|" but the
    sort value (a filename) may, so split on the last one."""
    sort_val, sep, hash_val = cursor.rpartition("|")
    if not sep or not hash_val:
        raise InvalidCursor(f"Malformed cursor: {cursor!r}")
    if not numeric:
        return sort_val, hash_val
    try:
        return float(sort_val), hash_val
    except ValueError as exc:
        raise InvalidCursor(f"Malformed cursor: {cursor!r}") from exc


class ImagePage(BaseModel):
    items: list[ImageSummary]
    next_cursor: Optional[str] = None
    total_count: int


# Sort key per sort name: a column, or an expression that is never NULL.
# file_created comes from st_birthtime, which Linux does not report, so the
# Created sort falls back to the modification time; a NULL key would make
# the keyset comparison NULL and stop pagination after one page.
SORT_COLUMNS = {
    "name": "filename",
    "date_modified": "file_modified",
    "date_created": "COALESCE(file_created, file_modified)",
    "size": "file_size",
    "aspect_ratio": "aspect_ratio",
}

# Video formats as stored in the format column (file extension, uppercase)
VIDEO_FORMATS = {ext.lstrip(".").upper() for ext in VIDEO_EXTENSIONS}

ASPECT_RATIO_FILTERS: dict[str, str] = {
    "portrait": "aspect_ratio < 0.9",
    "square": "aspect_ratio BETWEEN 0.9 AND 1.1",
    "landscape": "aspect_ratio BETWEEN 1.1 AND 2.0",
    "wide": "aspect_ratio > 2.0",
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
) -> str:
    """Append the date / aspect-ratio / media-type WHERE clauses shared by the
    image listing and ELO pair queries, adding their values to `params`.
    `prefix` qualifies column references (e.g. "i." when the images table is
    aliased)."""
    if date_from is not None:
        q += f" AND {prefix}file_modified >= ?"
        params.append(date_from)
    if date_to is not None:
        if len(date_to) == 10:
            # A bare date (the UI sends YYYY-MM-DD) means the whole day:
            # file_modified is a full timestamp, so compare with the next day.
            q += f" AND {prefix}file_modified < date(?, '+1 day')"
        else:
            q += f" AND {prefix}file_modified <= ?"
        params.append(date_to)
    if aspect_ratio_filter in ASPECT_RATIO_FILTERS:
        q += f" AND {prefix}{ASPECT_RATIO_FILTERS[aspect_ratio_filter]}"
    if media_type in ("video", "image"):
        placeholders = ",".join("?" * len(VIDEO_FORMATS))
        op = "IN" if media_type == "video" else "NOT IN"
        q += f" AND {prefix}format {op} ({placeholders})"
        params.extend(VIDEO_FORMATS)
    return q


@dataclass(frozen=True)
class ListingFilters:
    """The filters a grid applies; shared by the listing and its neighbours."""

    source_id: Optional[int] = None
    collection_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    aspect_ratio_filter: Optional[str] = None
    media_type: Optional[str] = None
    tags: Optional[list[str]] = None
    show_nsfw: bool = False
    elo_cut: Optional[EloCut] = None


def _apply_filters(q: str, p: list[object], f: ListingFilters) -> str:
    """Append the WHERE clauses for `f` to `q`, adding values to `p`."""
    if f.source_id is not None:
        q += f" AND {in_source_sql()}"
        p.append(f.source_id)
    if f.collection_id is not None:
        q += " AND content_hash IN (SELECT content_hash FROM collection_images WHERE collection_id = ?)"
        p.append(f.collection_id)
    q = append_media_filters(
        q, p,
        date_from=f.date_from,
        date_to=f.date_to,
        aspect_ratio_filter=f.aspect_ratio_filter,
        media_type=f.media_type,
    )
    for tag_name in f.tags or []:
        folder = tagged_folder(tag_name)
        if folder is not None:
            q += f" AND {in_folder_sql()}"
            p.extend(in_folder_params(folder))
            continue
        q += (
            " AND EXISTS ("
            "SELECT 1 FROM image_tags it JOIN tags t ON t.id = it.tag_id"
            " WHERE it.image_hash = content_hash AND t.name = ?"
            ")"
        )
        p.append(tag_name)
    if f.elo_cut is not None:
        sql, values = in_cut_sql(f.elo_cut)
        q += f" AND {sql}"
        p.extend(values)
    if not f.show_nsfw:
        q += f" AND {safe_sql()}"
    return q


def safe_sql(prefix: str = "") -> str:
    """SQL condition: the image is shown while NSFW images are hidden.
    `prefix` qualifies the images columns (e.g. "i.")."""
    return (
        f"{prefix}nsfw = 0"
        # Hidden if a member of an NSFW manual/static collection...
        f" AND {prefix}content_hash NOT IN ("
        "SELECT ci.content_hash FROM collection_images ci"
        " JOIN collections c ON c.id = ci.collection_id WHERE c.nsfw = 1)"
        # ...or if it lies in a source whose preset collection is NSFW
        # (presets have no collection_images rows; they match by source).
        f" AND {prefix}content_hash NOT IN ("
        "SELECT l.content_hash FROM image_locations l"
        " JOIN collections c ON c.source_id = l.source_id"
        " WHERE c.type = 'source_preset' AND c.nsfw = 1)"
    )


# An image's ELO score in the collection bound to its placeholder; images
# never voted on there score the default 1500.
_ELO_SCORE_SQL = (
    "COALESCE((SELECT e.score FROM elo_scores e"
    " WHERE e.content_hash = images.content_hash"
    " AND e.collection_id = ?), 1500.0)"
)


@dataclass(frozen=True)
class _SortKey:
    expr: str  # SQL for the key; may hold one placeholder
    params: tuple[object, ...]  # values for that placeholder
    alias: str  # the key's name in the SELECT list
    numeric: bool  # compare cursor values as numbers


def _sort_key(sort: str, elo_collection_id: Optional[int]) -> _SortKey:
    """The key a listing orders and pages by. Pass `elo_collection_id` with
    sort="elo" to order by that collection's ELO score (unscored = 1500)."""
    if sort == "elo" and elo_collection_id is not None:
        return _SortKey(
            _ELO_SCORE_SQL,
            (elo_collection_id,),
            "elo_score",
            True,
        )
    column = SORT_COLUMNS.get(sort, "filename")
    return _SortKey(column, (), "sort_key", column in _NUMERIC_SORT_COLUMNS)


# Sort keys whose cursor values are bound as numbers, not text.
_NUMERIC_SORT_COLUMNS = frozenset({"file_size", "aspect_ratio"})


_LIVE = "FROM images WHERE deleted = 0 AND archived = 0"


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
    elo_collection_id: Optional[int] = None,
    elo_cut: Optional[EloCut] = None,
) -> ImagePage:
    """Cursor-paginated image listing.

    Pass `elo_collection_id` with `sort="elo"` to order by per-collection ELO
    score (only meaningful within a collection). Images with no recorded score
    sort at the default 1500.
    """
    f = ListingFilters(
        source_id=source_id,
        collection_id=collection_id,
        date_from=date_from,
        date_to=date_to,
        aspect_ratio_filter=aspect_ratio_filter,
        media_type=media_type,
        tags=tags,
        show_nsfw=show_nsfw,
        elo_cut=elo_cut,
    )
    return listing_page(
        conn, f,
        cursor=cursor, limit=limit, sort=sort, direction=direction,
        elo_collection_id=elo_collection_id,
    )


def listing_page(
    conn: sqlite3.Connection,
    filters: ListingFilters,
    *,
    cursor: Optional[str] = None,
    limit: int = 200,
    sort: str = "name",
    direction: str = "asc",
    elo_collection_id: Optional[int] = None,
) -> ImagePage:
    """A page of the listing that sort, direction and filters define; see
    `list_images`."""
    key = _sort_key(sort, elo_collection_id)
    return _page(conn, filters, key, direction, cursor, limit)


def _page(
    conn: sqlite3.Connection,
    f: ListingFilters,
    key: _SortKey,
    direction: str,
    cursor: Optional[str],
    limit: int,
) -> ImagePage:
    if direction not in ("asc", "desc"):
        direction = "asc"

    count_params: list[object] = []
    count_sql = _apply_filters(f"SELECT COUNT(*) {_LIVE}", count_params, f)
    total = conn.execute(count_sql, count_params).fetchone()[0]

    # Select the sort key too so the cursor can carry its real value; extra
    # columns are ignored when building ImageSummary. The key's placeholder
    # (ELO) sits in the SELECT list, so its value leads the parameters.
    select_cols = [*SUMMARY_COLUMNS, f"{key.expr} AS {key.alias}"]
    params: list[object] = list(key.params)
    sql = _apply_filters(f"SELECT {', '.join(select_cols)} {_LIVE}", params, f)

    if cursor is not None:
        op = ">" if direction == "asc" else "<"
        sort_val, hash_val = _parse_cursor(cursor, numeric=key.numeric)
        sql += f" AND ({key.expr}, content_hash) {op} (?, ?)"
        params.extend([*key.params, sort_val, hash_val])

    sql += f" ORDER BY {key.alias} {direction}, content_hash {direction}"
    sql += " LIMIT ?"
    params.append(limit + 1)  # fetch one extra to detect next page

    rows = conn.execute(sql, params).fetchall()

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    items = [summary_from_row(r) for r in rows]

    next_cursor = None
    if has_next and rows:
        last_row = rows[-1]
        next_cursor = f"{last_row[key.alias]}|{last_row['content_hash']}"

    return ImagePage(items=items, next_cursor=next_cursor, total_count=total)


class Neighbors(BaseModel):
    """A window of a listing around one image."""

    before: list[ImageSummary]  # nearest last, in listing order
    after: list[ImageSummary]  # nearest first
    position: int  # 0-based place of the image in the listing
    total_count: int


def neighbors(
    conn: sqlite3.Connection,
    content_hash: str,
    *,
    window: int = 50,
    sort: str = "name",
    direction: str = "asc",
    elo_collection_id: Optional[int] = None,
    filters: Optional[ListingFilters] = None,
) -> Optional[Neighbors]:
    """Up to `window` images on each side of `content_hash` in the listing
    that sort, direction and filters define, wherever it falls in it.
    None if the image does not exist. An image the filters exclude still
    has neighbours: those around the place it would sort into."""
    if direction not in ("asc", "desc"):
        direction = "asc"
    filters = filters or ListingFilters()
    key = _sort_key(sort, elo_collection_id)
    row = conn.execute(
        f"SELECT {key.expr} FROM images WHERE content_hash = ?",
        (*key.params, content_hash),
    ).fetchone()
    if row is None:
        return None
    cursor = f"{row[0]}|{content_hash}"
    reverse = "desc" if direction == "asc" else "asc"

    after = _page(conn, filters, key, direction, cursor, window)
    before = _page(conn, filters, key, reverse, cursor, window)

    # The image's position: how many listed rows sort ahead of it.
    op = "<" if direction == "asc" else ">"
    params: list[object] = []
    sql = _apply_filters(f"SELECT COUNT(*) {_LIVE}", params, filters)
    sql += f" AND ({key.expr}, content_hash) {op} (?, ?)"
    params.extend([*key.params, row[0], content_hash])
    position = conn.execute(sql, params).fetchone()[0]

    return Neighbors(
        before=list(reversed(before.items)),
        after=after.items,
        position=position,
        total_count=after.total_count,
    )


class SequenceItem(BaseModel):
    """One image of a listing, as a slideshow walks it."""

    content_hash: str
    filename: str
    score: Optional[float] = None  # ELO score in the collection browsed


def sequence(
    conn: sqlite3.Connection,
    *,
    sort: str = "name",
    direction: str = "asc",
    elo_collection_id: Optional[int] = None,
    score_collection_id: Optional[int] = None,
    filters: Optional[ListingFilters] = None,
) -> list[SequenceItem]:
    """The whole listing that sort, direction and filters define, in order.
    Pass `score_collection_id` to give each image its ELO score there."""
    if direction not in ("asc", "desc"):
        direction = "asc"
    key = _sort_key(sort, elo_collection_id)
    params: list[object] = list(key.params)
    score = "NULL"
    if score_collection_id is not None:
        score = _ELO_SCORE_SQL
        params.append(score_collection_id)
    sql = _apply_filters(
        f"SELECT content_hash, filename, {score} AS score, {key.expr} AS {key.alias} {_LIVE}",
        params,
        filters or ListingFilters(),
    )
    sql += f" ORDER BY {key.alias} {direction}, content_hash {direction}"
    return [
        SequenceItem(content_hash=r["content_hash"], filename=r["filename"], score=r["score"])
        for r in conn.execute(sql, params)
    ]


# The file version whose metadata an image shows: its primary location's,
# else the one read last (its file may be gone). Binds the image key once.
_SHOWN_VERSION = """
    SELECT m.file_hash FROM file_metadata m
    WHERE m.content_hash = :key
    ORDER BY m.file_hash IS (
        SELECT l.file_hash FROM image_locations l JOIN images i
          ON l.source_id = i.source_id AND l.relative_path = i.relative_path
        WHERE i.content_hash = :key) DESC,
      m.extracted_at DESC
    LIMIT 1
"""

# The image's other file versions whose generation tool, prompt or negative
# prompt differ from the shown one's. The rest of a file's metadata (EXIF,
# PNG text, and the raw parameters, which hold all PNG text) changes
# whenever a tool writes keywords or a comment into it, which tags already
# carry; and settings such as the seed cannot differ for the same picture.
_DIFFERING_VERSIONS = f"""
    SELECT COUNT(*) FROM file_metadata o, file_metadata shown
    WHERE shown.file_hash = ({_SHOWN_VERSION})
      AND o.content_hash = :key AND o.file_hash != shown.file_hash
      AND (o.ai_tool IS NOT shown.ai_tool OR o.prompt IS NOT shown.prompt
           OR o.negative_prompt IS NOT shown.negative_prompt)
"""


def get_image(conn: sqlite3.Connection, content_hash: str) -> Optional[ImageDetail]:
    """Get full image details including metadata. Returns archived images too."""
    row = conn.execute(
        f"""SELECT i.*, m.ai_tool, m.prompt, m.negative_prompt,
                  m.raw_params, m.exif_data, m.png_text,
                  ({_DIFFERING_VERSIONS}) AS other_versions
           FROM images i
           LEFT JOIN file_metadata m ON m.file_hash = ({_SHOWN_VERSION})
           WHERE i.content_hash = :key AND i.deleted = 0""",
        {"key": content_hash},
    ).fetchone()

    if row is None:
        return None

    return ImageDetail(**dict(row), folder_tags=folder_tags(conn, content_hash))


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
    """Resolve the full file path for an image: its primary location, or
    another copy if that file has gone missing since the last scan.
    None if the image is unknown or deleted."""
    paths = resolve_paths(conn, content_hash)
    if not paths:
        return None
    return next((p for p in paths if Path(p).is_file()), paths[0])
