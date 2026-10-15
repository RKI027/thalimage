"""Voting statistics for a collection: how matches spread over the images
voting can draw, how settled their scores are, and how pairs have met."""

import json
import sqlite3
from typing import Optional

from pydantic import BaseModel

from thalimage.services.elo_ranking import member_sql, ranked_sql
from thalimage.services.image_service import safe_sql


class CoveredImage(BaseModel):
    """An image voting can draw. `matches` counts every vote it took part in
    there; `score` and `rank` are None until it has been voted on; `nsfw`
    says whether it is hidden while NSFW images are hidden."""

    content_hash: str
    filename: str
    nsfw: bool
    matches: int
    score: Optional[float]
    rank: Optional[int]


class PairStats(BaseModel):
    """How the possible pairs of covered images have met: at least once,
    more than once, and the most any one pair has."""

    met: int
    possible: int
    repeated: int
    most_meetings: int


class Meeting(BaseModel):
    winner: str
    loser: str
    count: int


class EloStats(BaseModel):
    """`images` from the top of the ranking down, unvoted last; `top` the
    first ranked of them, with `head_to_head` the results among those."""

    images: list[CoveredImage]
    pairs: PairStats
    top: list[CoveredImage]
    head_to_head: list[Meeting]


# The images voting can draw: members, neither deleted nor archived.
_COVERED = f"""covered AS (
    SELECT i.content_hash, i.filename, NOT ({safe_sql("i.")}) AS nsfw
    FROM images i JOIN collections c ON c.id = :cid
    WHERE i.deleted = 0 AND i.archived = 0 AND {member_sql("c", "i.content_hash")})"""

# Votes between two covered images.
_MEETINGS = """meetings AS (
    SELECT v.winner_hash, v.loser_hash FROM votes v
    WHERE v.collection_id = :cid
    AND v.winner_hash IN (SELECT content_hash FROM covered)
    AND v.loser_hash IN (SELECT content_hash FROM covered))"""


def collection_stats(conn: sqlite3.Connection, collection_id: int, *, top: int = 20) -> Optional[EloStats]:
    """The collection's voting statistics; None if there is no such collection."""
    if conn.execute("SELECT 1 FROM collections WHERE id = ?", (collection_id,)).fetchone() is None:
        return None
    params = {"cid": collection_id}
    images = [
        CoveredImage(**dict(r))
        for r in conn.execute(
            f"""WITH {_COVERED},
               ranked AS (SELECT content_hash, score, RANK() OVER (ORDER BY score DESC) AS rank
                          FROM ({ranked_sql(":cid")}))
               SELECT cv.content_hash, cv.filename, cv.nsfw, COALESCE(e.matches, 0) AS matches,
                      r.score, r.rank
               FROM covered cv
               LEFT JOIN elo_scores e ON e.collection_id = :cid AND e.content_hash = cv.content_hash
               LEFT JOIN ranked r ON r.content_hash = cv.content_hash
               ORDER BY r.score IS NULL, r.score DESC, cv.content_hash DESC""",
            params,
        )
    ]
    met, repeated, most = conn.execute(
        f"""WITH {_COVERED}, {_MEETINGS},
           pairs AS (SELECT COUNT(*) AS n FROM meetings
                     GROUP BY MIN(winner_hash, loser_hash), MAX(winner_hash, loser_hash))
           SELECT COUNT(*), COUNT(*) FILTER (WHERE n > 1), COALESCE(MAX(n), 0) FROM pairs""",
        params,
    ).fetchone()
    n = len(images)
    leaders = [i for i in images if i.rank is not None][:top]
    head_to_head = [
        Meeting(**dict(r))
        for r in conn.execute(
            f"""WITH {_COVERED}, {_MEETINGS}
               SELECT winner_hash AS winner, loser_hash AS loser, COUNT(*) AS count
               FROM meetings
               WHERE winner_hash IN (SELECT value FROM json_each(:top))
               AND loser_hash IN (SELECT value FROM json_each(:top))
               GROUP BY winner_hash, loser_hash
               ORDER BY count DESC, winner, loser""",
            {**params, "top": json.dumps([i.content_hash for i in leaders])},
        )
    ]
    return EloStats(
        images=images,
        pairs=PairStats(met=met, possible=n * (n - 1) // 2, repeated=repeated, most_meetings=most),
        top=leaders,
        head_to_head=head_to_head,
    )
