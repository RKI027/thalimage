"""ELO voting service: pair selection, vote recording, rankings."""

import random
import sqlite3
from typing import Any

from thalimage.services.image_service import ImageSummary

K_FACTOR = 32


def get_pair(
    conn: sqlite3.Connection, collection_id: int
) -> tuple[ImageSummary, ImageSummary]:
    """Select two images from a collection for comparison.

    Favors images with fewer matches to ensure even coverage.
    """
    rows = conn.execute(
        """SELECT i.content_hash, i.filename, i.source_id, i.relative_path,
                  i.width, i.height, i.aspect_ratio, i.format, i.thumb_generated,
                  COALESCE(e.matches, 0) AS matches
           FROM collection_images ci
           JOIN images i ON ci.content_hash = i.content_hash
           LEFT JOIN elo_scores e ON i.content_hash = e.content_hash
                AND e.collection_id = ci.collection_id
           WHERE ci.collection_id = ? AND i.deleted = 0
           ORDER BY matches ASC, RANDOM()
        """,
        (collection_id,),
    ).fetchall()

    if len(rows) < 2:
        raise ValueError(
            f"Collection {collection_id} needs at least 2 images for voting"
        )

    # Pick from bottom quartile by match count
    quartile_size = max(2, len(rows) // 4)
    candidates = rows[:quartile_size]
    picked = random.sample(candidates, 2)

    return (
        ImageSummary(**{k: picked[0][k] for k in ImageSummary.model_fields}),
        ImageSummary(**{k: picked[1][k] for k in ImageSummary.model_fields}),
    )


def record_vote(
    conn: sqlite3.Connection,
    collection_id: int,
    *,
    winner_hash: str,
    loser_hash: str,
) -> None:
    """Record a vote and update ELO scores."""
    # Get current scores (or default 1500)
    winner_score = _get_score(conn, collection_id, winner_hash)
    loser_score = _get_score(conn, collection_id, loser_hash)

    # Calculate expected scores
    e_winner = 1.0 / (1.0 + 10.0 ** ((loser_score - winner_score) / 400.0))
    e_loser = 1.0 - e_winner

    # Update scores
    new_winner = winner_score + K_FACTOR * (1.0 - e_winner)
    new_loser = loser_score + K_FACTOR * (0.0 - e_loser)

    # Record the vote
    conn.execute(
        "INSERT INTO votes (collection_id, winner_hash, loser_hash) VALUES (?, ?, ?)",
        (collection_id, winner_hash, loser_hash),
    )

    # Upsert ELO scores
    _upsert_score(conn, collection_id, winner_hash, new_winner)
    _upsert_score(conn, collection_id, loser_hash, new_loser)

    conn.commit()


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
