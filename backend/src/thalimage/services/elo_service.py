"""ELO voting service: pair selection, vote recording, rankings."""

import random
import sqlite3
from typing import Any, Optional

from thalimage.services.image_service import (
    ImageSummary,
    append_media_filters,
    summary_columns_sql,
    summary_from_row,
)

K_FACTOR = 32


def get_pair(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    source_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    aspect_ratio_filter: Optional[str] = None,
    media_type: Optional[str] = None,
    show_nsfw: bool = False,
) -> tuple[ImageSummary, ImageSummary]:
    """Select two images from a collection for comparison.

    For source_preset collections pass source_id; for manual collections leave it None.
    The pool is the live, unarchived images that pass the given filters;
    the pair is drawn uniformly from its least-matched quarter.
    """
    select = (
        f"SELECT {summary_columns_sql('i.')}, COALESCE(e.matches, 0) AS matches"
        " FROM images i LEFT JOIN elo_scores e"
        " ON e.content_hash = i.content_hash AND e.collection_id = ?"
        " WHERE i.deleted = 0 AND i.archived = 0"
    )
    params: list[object] = [collection_id]
    if source_id is not None:
        q = select + (
            " AND i.content_hash IN"
            " (SELECT content_hash FROM image_locations WHERE source_id = ?)"
        )
        params.append(source_id)
    else:
        q = select + (
            " AND i.content_hash IN"
            " (SELECT content_hash FROM collection_images WHERE collection_id = ?)"
        )
        params.append(collection_id)

    q = append_media_filters(
        q, params,
        prefix="i.",
        date_from=date_from,
        date_to=date_to,
        aspect_ratio_filter=aspect_ratio_filter,
        media_type=media_type,
    )
    if not show_nsfw:
        q += " AND i.nsfw = 0"
    q += " ORDER BY matches ASC, RANDOM()"

    rows = conn.execute(q, params).fetchall()

    if len(rows) < 2:
        raise ValueError(
            f"Collection {collection_id} needs at least 2 images for voting"
        )

    # Pick from bottom quartile by match count
    quartile_size = max(2, len(rows) // 4)
    candidates = rows[:quartile_size]
    picked = random.sample(candidates, 2)

    return summary_from_row(picked[0]), summary_from_row(picked[1])


class CollectionNotFound(LookupError):
    """The vote names a collection that does not exist."""


class InvalidVote(ValueError):
    """The vote cannot be recorded as given."""


def record_vote(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    winner_hash: str,
    loser_hash: str,
) -> None:
    """Record a vote and update both ELO scores.

    The reads and writes run in one BEGIN IMMEDIATE transaction, so two votes
    touching the same image cannot both start from the old score.
    """
    if winner_hash == loser_hash:
        raise InvalidVote("An image cannot be voted against itself")

    conn.execute("BEGIN IMMEDIATE")
    try:
        coll = conn.execute(
            "SELECT type, source_id FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        if coll is None:
            raise CollectionNotFound(f"Collection {collection_id} not found")
        for h in (winner_hash, loser_hash):
            if not _in_collection(conn, collection_id, coll["type"], coll["source_id"], h):
                raise InvalidVote(f"Image {h} is not in collection {collection_id}")

        winner_score = _get_score(conn, collection_id, winner_hash)
        loser_score = _get_score(conn, collection_id, loser_hash)

        e_winner = 1.0 / (1.0 + 10.0 ** ((loser_score - winner_score) / 400.0))
        e_loser = 1.0 - e_winner
        new_winner = winner_score + K_FACTOR * (1.0 - e_winner)
        new_loser = loser_score + K_FACTOR * (0.0 - e_loser)

        conn.execute(
            "INSERT INTO votes (collection_id, winner_hash, loser_hash) VALUES (?, ?, ?)",
            (collection_id, winner_hash, loser_hash),
        )
        _upsert_score(conn, collection_id, winner_hash, new_winner)
        _upsert_score(conn, collection_id, loser_hash, new_loser)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def _in_collection(
    conn: sqlite3.Connection,
    collection_id: int,
    coll_type: str,
    source_id: Optional[int],
    content_hash: str,
) -> bool:
    """Whether a live image belongs to the collection. Source presets hold no
    collection_images rows; their members are the source's images."""
    if coll_type == "source_preset":
        row = conn.execute(
            "SELECT 1 FROM images i JOIN image_locations l ON l.content_hash = i.content_hash"
            " WHERE i.content_hash = ? AND l.source_id = ? AND i.deleted = 0",
            (content_hash, source_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM collection_images ci"
            " JOIN images i ON i.content_hash = ci.content_hash"
            " WHERE ci.collection_id = ? AND ci.content_hash = ? AND i.deleted = 0",
            (collection_id, content_hash),
        ).fetchone()
    return row is not None


def get_rankings(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get ranked images by ELO score for a collection."""
    rows = conn.execute(
        """SELECT e.content_hash, e.score, e.matches, i.filename
           FROM elo_scores e
           JOIN images i ON e.content_hash = i.content_hash
           WHERE e.collection_id = ?
           ORDER BY e.score DESC
           LIMIT ?
        """,
        (collection_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_score(conn: sqlite3.Connection, collection_id: int, content_hash: str) -> float:
    row = conn.execute(
        "SELECT score FROM elo_scores WHERE content_hash = ? AND collection_id = ?",
        (content_hash, collection_id),
    ).fetchone()
    return float(row["score"]) if row else 1500.0


def _upsert_score(
    conn: sqlite3.Connection,
    collection_id: int,
    content_hash: str,
    score: float,
) -> None:
    conn.execute(
        """INSERT INTO elo_scores (content_hash, collection_id, score, matches)
           VALUES (?, ?, ?, 1)
           ON CONFLICT(content_hash, collection_id) DO UPDATE SET
            score = ?,
            matches = matches + 1,
            updated_at = datetime('now')
        """,
        (content_hash, collection_id, score, score),
    )
