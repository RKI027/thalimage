"""Source removal."""

import sqlite3

from thalimage.services.collection_service import purge_collection
from thalimage.services.locations import sync_images


def delete_source(conn: sqlite3.Connection, source_id: int) -> bool:
    """Delete a source and everything that exists only because of it.

    Content that also lies in another source survives, with its
    collections, votes and tags, and is re-pointed at that other copy.
    Content found only here is removed with all its dependent rows.
    Returns False if there is no such source. Commits.
    """
    if conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone() is None:
        return False
    with conn:
        for preset in conn.execute(
            "SELECT id FROM collections WHERE source_id = ? AND type = 'source_preset'",
            (source_id,),
        ).fetchall():
            purge_collection(conn, preset["id"])

        located_here = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT content_hash FROM image_locations WHERE source_id = ?",
                (source_id,),
            )
        ]
        conn.execute("DELETE FROM image_locations WHERE source_id = ?", (source_id,))
        sync_images(conn, located_here)

        # Whatever still points here has no copy left anywhere (sync_images
        # moved the rest), including images soft-deleted from this source.
        orphans = [
            r[0] for r in conn.execute(
                "SELECT content_hash FROM images WHERE source_id = ?", (source_id,)
            )
        ]
        if orphans:
            marks = ",".join("?" * len(orphans))
            conn.execute(f"DELETE FROM image_metadata WHERE content_hash IN ({marks})", orphans)
            conn.execute(f"DELETE FROM collection_images WHERE content_hash IN ({marks})", orphans)
            conn.execute(f"DELETE FROM elo_scores WHERE content_hash IN ({marks})", orphans)
            conn.execute(
                f"DELETE FROM votes WHERE winner_hash IN ({marks}) OR loser_hash IN ({marks})",
                orphans + orphans,
            )
            # image_tags and image_locations cascade.
            conn.execute(f"DELETE FROM images WHERE content_hash IN ({marks})", orphans)
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    return True
