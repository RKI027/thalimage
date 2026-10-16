"""Changing an image's key, merging it into the image that already holds
the new key if there is one."""

import json
import sqlite3

from thalimage.services.elo_service import replay_scores
from thalimage.services.locations import EARLIEST_CREATED

# Tables holding an image key, and its column. votes is handled apart: a
# vote holds two keys, and merging can turn it into a self-match.
_KEYED = (
    ("file_metadata", "content_hash"),
    ("image_tags", "image_hash"),
    ("collection_images", "content_hash"),
    ("elo_scores", "content_hash"),
    ("image_locations", "content_hash"),
)


def rekey_image(conn: sqlite3.Connection, old: str, new: str) -> None:
    """Give the image keyed `old` the key `new`, with its tags, collection
    memberships, votes, scores, locations and file versions' metadata. If an
    image is keyed `new` already, the two merge: tags, memberships and file
    versions combine, votes between them are dropped, and the collections
    whose votes moved are replayed.

    Does nothing if no image is keyed `old`. Runs inside the caller's
    transaction; does not commit.
    """
    if old == new or not _exists(conn, old):
        return
    merging = _exists(conn, new)
    if merging:
        _combine_images(conn, old, new)
    else:
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(images)")]
        copied = ", ".join("?" if c == "content_hash" else c for c in columns)
        conn.execute(
            f"INSERT INTO images ({', '.join(columns)})"
            f" SELECT {copied} FROM images WHERE content_hash = ?",
            (new, old),
        )
    for table, column in _KEYED:
        conn.execute(f"UPDATE OR IGNORE {table} SET {column} = ? WHERE {column} = ?", (new, old))
        conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (old,))
    voted_in = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT collection_id FROM votes WHERE ? IN (winner_hash, loser_hash)", (old,)
        )
    ]
    conn.execute("UPDATE votes SET winner_hash = ? WHERE winner_hash = ?", (new, old))
    conn.execute("UPDATE votes SET loser_hash = ? WHERE loser_hash = ?", (new, old))
    if merging:
        conn.execute("DELETE FROM votes WHERE winner_hash = loser_hash")
        for collection_id in voted_in:
            replay_scores(conn, collection_id)
    conn.execute("DELETE FROM images WHERE content_hash = ?", (old,))


def _exists(conn: sqlite3.Connection, key: str) -> bool:
    return conn.execute("SELECT 1 FROM images WHERE content_hash = ?", (key,)).fetchone() is not None


def _combine_images(conn: sqlite3.Connection, old: str, new: str) -> None:
    """Fold the flags and dates of the image keyed `old` into the one keyed
    `new`: archived or deleted only if both are, NSFW if either is, created
    at the earliest date known, with the tag names imported from either's
    files, so that a tag removed from either is not imported again."""
    o = conn.execute(
        "SELECT archived, deleted, nsfw, file_created, file_tags FROM images WHERE content_hash = ?",
        (old,),
    ).fetchone()
    n = conn.execute("SELECT file_tags FROM images WHERE content_hash = ?", (new,)).fetchone()
    imported = set(json.loads(o["file_tags"] or "[]")) | set(json.loads(n["file_tags"] or "[]"))
    conn.execute(
        f"""UPDATE images SET archived = archived AND :archived,
                   deleted = deleted AND :deleted,
                   nsfw = nsfw OR :nsfw,
                   file_created = {EARLIEST_CREATED.format(new=":file_created", old="file_created")},
                   file_tags = :file_tags
            WHERE content_hash = :key""",
        {**dict(o), "file_tags": json.dumps(sorted(imported)), "key": new},
    )
