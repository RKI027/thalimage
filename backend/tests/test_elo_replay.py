"""Replaying a collection's votes to recompute its ELO scores."""

import sqlite3

from tests.test_elo_service import _seed_collection_with_images
from thalimage.services.elo_service import get_rankings, record_vote, replay_scores

# (winner, loser) by index into the seeded images.
VOTES = [(0, 1), (2, 0), (0, 3), (1, 2), (3, 1), (0, 2), (2, 3)]


def _standings(conn: sqlite3.Connection, cid: int) -> dict[str, tuple[float, int]]:
    return {r.image.content_hash: (round(r.score, 9), r.matches) for r in get_rankings(conn, cid).items}


def _vote_all(conn: sqlite3.Connection, cid: int, hashes: list[str], votes: list[tuple[int, int]]) -> None:
    for winner, loser in votes:
        record_vote(conn, cid, winner_hash=hashes[winner], loser_hash=hashes[loser])


def _collection_of(conn: sqlite3.Connection, hashes: list[str]) -> int:
    """Another collection holding the same images."""
    cur = conn.execute("INSERT INTO collections (name) VALUES ('Other')")
    conn.executemany(
        "INSERT INTO collection_images (collection_id, content_hash) VALUES (?, ?)",
        [(cur.lastrowid, h) for h in hashes],
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def test_replay_reproduces_the_recorded_scores(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=4)
    _vote_all(db, cid, hashes, VOTES)
    before = _standings(db, cid)

    replay_scores(db, cid)

    assert _standings(db, cid) == before


def test_replay_after_losing_a_vote_scores_as_if_it_never_happened(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=4)
    _vote_all(db, cid, hashes, VOTES)
    db.execute(
        "DELETE FROM votes WHERE collection_id = ? AND winner_hash = ? AND loser_hash = ?",
        (cid, hashes[1], hashes[2]),
    )

    replay_scores(db, cid)

    other = _collection_of(db, hashes)
    _vote_all(db, other, hashes, [v for v in VOTES if v != (1, 2)])
    assert _standings(db, cid) == _standings(db, other)


def test_an_image_left_without_votes_loses_its_score(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=3)
    _vote_all(db, cid, hashes, [(0, 1), (0, 2)])
    db.execute("DELETE FROM votes WHERE loser_hash = ?", (hashes[2],))

    replay_scores(db, cid)

    assert set(_standings(db, cid)) == {hashes[0], hashes[1]}


def test_replay_leaves_other_collections_alone(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=4)
    other = _collection_of(db, hashes)
    _vote_all(db, other, hashes, VOTES)
    before = _standings(db, other)
    db.execute("DELETE FROM votes WHERE collection_id = ? AND rowid = (SELECT MIN(rowid) FROM votes)", (other,))

    replay_scores(db, cid)

    assert _standings(db, other) == before
