"""Pictures changed in place: offering to keep the image across an edit.

A file whose picture changed gets a new key, and the image it held loses
that copy. When that image has no copy left and the two pictures look
alike, the scan records them as a possible edit; the user then merges them
into one image or keeps them separate.
"""

import sqlite3
from collections.abc import Iterable
from typing import Optional

from pydantic import BaseModel

from thalimage.core.perceptual_hash import distance


class PossibleEdit(BaseModel):
    """An earlier picture this image may be an edit of."""

    old_hash: str
    # How far apart the two pictures look, from 0 (the same) to 1.
    distance: float


# SQL condition on picture_edits `e`: the pair is still to be decided. Only
# while the old image has no copy left: one back on disk is its own image.
_UNDECIDED = (
    "e.kept_separate = 0 AND EXISTS ("
    "SELECT 1 FROM images o WHERE o.content_hash = e.old_hash AND o.deleted = 1)"
)


def is_possible_edit_sql(hash_col: str = "content_hash") -> str:
    """SQL condition: the image may be an edit of an earlier picture."""
    return f"EXISTS (SELECT 1 FROM picture_edits e WHERE e.new_hash = {hash_col} AND {_UNDECIDED})"


def record_edits(
    conn: sqlite3.Connection, replaced: Iterable[tuple[str, str]], threshold: float
) -> None:
    """Record as possible edits the (old, new) keys of pictures replaced at
    a path whose old image has no copy left, where the two look alike
    within `threshold`. A pair already recorded keeps its decision.

    Runs inside the caller's transaction; does not commit.
    """
    for old, new in replaced:
        row = conn.execute(
            "SELECT o.perceptual_hash AS old, n.perceptual_hash AS new"
            " FROM images o, images n"
            " WHERE o.content_hash = ? AND n.content_hash = ? AND o.deleted = 1",
            (old, new),
        ).fetchone()
        if row is None or row["old"] is None or row["new"] is None:
            continue
        apart = distance(row["old"], row["new"])
        if apart <= threshold:
            conn.execute(
                "INSERT OR IGNORE INTO picture_edits (old_hash, new_hash, distance)"
                " VALUES (?, ?, ?)",
                (old, new, apart),
            )


def possible_edit_of(conn: sqlite3.Connection, new_hash: str) -> Optional[PossibleEdit]:
    """The earlier picture a live image may be an edit of, the closest if
    there are several."""
    row = conn.execute(
        f"SELECT e.old_hash, e.distance FROM picture_edits e"
        f" JOIN images n ON n.content_hash = e.new_hash"
        f" WHERE e.new_hash = ? AND n.deleted = 0 AND {_UNDECIDED}"
        f" ORDER BY e.distance, e.found_at LIMIT 1",
        (new_hash,),
    ).fetchone()
    return PossibleEdit(**dict(row)) if row else None


def merge(conn: sqlite3.Connection, new_hash: str) -> Optional[str]:
    """Make the image an edit of its earlier picture: the earlier image's
    tags, collections, votes, scores and file versions move to it. Pending
    edits of the earlier image become edits of this one. The earlier key,
    now retired, or None if there was no possible edit. Commits."""
    # Imported here: identity leads back to image_service, which reads
    # possible edits from this module.
    from thalimage.services.identity import rekey_image

    edit = possible_edit_of(conn, new_hash)
    if edit is None:
        return None
    old = edit.old_hash
    with conn:
        conn.execute("DELETE FROM picture_edits WHERE old_hash = ?", (old,))
        conn.execute(
            "UPDATE OR IGNORE picture_edits SET new_hash = ? WHERE new_hash = ?", (new_hash, old)
        )
        conn.execute("DELETE FROM picture_edits WHERE new_hash = ?", (old,))
        rekey_image(conn, old, new_hash)
    return old


def keep_separate(conn: sqlite3.Connection, new_hash: str) -> None:
    """Keep the image apart from its closest earlier picture; that pair is
    not offered again. Commits."""
    edit = possible_edit_of(conn, new_hash)
    if edit is None:
        return
    with conn:
        conn.execute(
            "UPDATE picture_edits SET kept_separate = 1 WHERE old_hash = ? AND new_hash = ?",
            (edit.old_hash, new_hash),
        )
