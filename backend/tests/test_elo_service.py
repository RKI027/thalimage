"""Tests for ELO voting service."""

import sqlite3

import pytest

from thalimage.services.elo_service import get_pair, get_rankings, record_vote


def _seed_collection_with_images(conn: sqlite3.Connection, n: int = 5) -> tuple[int, list[str]]:
    """Create a source, images, a collection, and add images to it."""
    conn.execute(
        "INSERT INTO sources (path, label, recursive) VALUES (?, ?, ?)",
        ("/test", "test", True),
    )
    conn.commit()

    hashes = []
    for i in range(n):
        h = f"hash_{i:04d}"
        conn.execute(
            """INSERT INTO images
               (content_hash, filename, source_id, relative_path,
                file_size, width, height, aspect_ratio, format,
                file_modified, thumb_generated)
               VALUES (?, ?, 1, ?, 1000, 100, 100, 1.0, 'PNG', '2024-01-01T00:00:00', 1)
            """,
            (h, f"img_{i}.png", f"img_{i}.png"),
        )
        hashes.append(h)

    conn.execute("INSERT INTO collections (name) VALUES (?)", ("Test Collection",))
    conn.commit()
    cid = conn.execute("SELECT id FROM collections ORDER BY id DESC LIMIT 1").fetchone()[0]

    for h in hashes:
        conn.execute(
            "INSERT INTO collection_images (collection_id, content_hash) VALUES (?, ?)",
            (cid, h),
        )
    conn.commit()

    return cid, hashes


def test_get_pair_returns_two_different_images(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=5)
    left, right = get_pair(db, cid)
    assert left.content_hash != right.content_hash
    assert left.content_hash in hashes
    assert right.content_hash in hashes


def test_get_pair_requires_minimum_two_images(db: sqlite3.Connection) -> None:
    cid, _ = _seed_collection_with_images(db, n=1)
    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid)


def test_get_pair_empty_collection(db: sqlite3.Connection) -> None:
    db.execute("INSERT INTO collections (name) VALUES (?)", ("Empty",))
    db.commit()
    cid = db.execute("SELECT id FROM collections ORDER BY id DESC LIMIT 1").fetchone()[0]
    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid)


def test_record_vote_updates_scores(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=2)
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])

    rankings = get_rankings(db, cid)
    assert len(rankings) == 2
    winner = next(r for r in rankings if r["content_hash"] == hashes[0])
    loser = next(r for r in rankings if r["content_hash"] == hashes[1])
    assert winner["score"] > 1500.0
    assert loser["score"] < 1500.0


def test_elo_calculation_correctness(db: sqlite3.Connection) -> None:
    """K=32, both start at 1500. Expected: 0.5 each. Winner gets +16, loser -16."""
    cid, hashes = _seed_collection_with_images(db, n=2)
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])

    rankings = get_rankings(db, cid)
    winner = next(r for r in rankings if r["content_hash"] == hashes[0])
    loser = next(r for r in rankings if r["content_hash"] == hashes[1])
    assert abs(winner["score"] - 1516.0) < 0.01
    assert abs(loser["score"] - 1484.0) < 0.01


def test_get_rankings_ordered_by_score_desc(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=3)
    # Make hash_0 win twice
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[2])

    rankings = get_rankings(db, cid)
    assert rankings[0]["content_hash"] == hashes[0]
    scores = [r["score"] for r in rankings]
    assert scores == sorted(scores, reverse=True)


def test_vote_creates_audit_record(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=2)
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])

    votes = db.execute("SELECT * FROM votes").fetchall()
    assert len(votes) == 1
    v = dict(votes[0])
    assert v["winner_hash"] == hashes[0]
    assert v["loser_hash"] == hashes[1]
    assert v["collection_id"] == cid


def test_vote_increments_matches(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=2)
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])
    record_vote(db, cid, winner_hash=hashes[1], loser_hash=hashes[0])

    rankings = get_rankings(db, cid)
    for r in rankings:
        assert r["matches"] == 2


def test_get_pair_favors_fewer_matches(db: sqlite3.Connection) -> None:
    """After voting on a pair many times, the other images should be picked."""
    cid, hashes = _seed_collection_with_images(db, n=4)
    # Vote on hashes[0] vs hashes[1] many times
    for _ in range(20):
        record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])

    # Get many pairs; hashes[2] and hashes[3] (0 matches) should appear most
    seen: dict[str, int] = {h: 0 for h in hashes}
    for _ in range(30):
        left, right = get_pair(db, cid)
        seen[left.content_hash] += 1
        seen[right.content_hash] += 1

    # The under-voted images should appear more than the over-voted ones
    assert seen[hashes[2]] + seen[hashes[3]] > seen[hashes[0]] + seen[hashes[1]]
