"""Tests for ELO voting service."""

import sqlite3

import pytest

from tests.helpers import ensure_source, insert_image
from thalimage.services.elo_service import get_pair, get_rankings, record_vote


def _seed_collection_with_images(conn: sqlite3.Connection, n: int = 5) -> tuple[int, list[str]]:
    """Create a source, images, a manual collection, and add images to it."""
    hashes = [
        insert_image(conn, f"hash_{i:04d}", filename=f"img_{i}.png", thumb_generated=True)
        for i in range(n)
    ]

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


def _seed_source_preset(
    conn: sqlite3.Connection, n: int = 5, *, dates: list[str] | None = None
) -> tuple[int, int, list[str]]:
    """Create a source, images, and a source_preset collection (no collection_images rows)."""
    sid = ensure_source(conn, "/src")
    hashes = [
        insert_image(
            conn,
            f"src_hash_{i:04d}",
            source_id=sid,
            filename=f"src_{i}.png",
            file_modified=dates[i] if dates else "2024-06-01T00:00:00",
            thumb_generated=True,
        )
        for i in range(n)
    ]

    conn.execute(
        "INSERT INTO collections (name, type, source_id) VALUES (?, 'source_preset', ?)",
        ("Source Preset", sid),
    )
    conn.commit()
    cid = conn.execute("SELECT id FROM collections ORDER BY id DESC LIMIT 1").fetchone()[0]

    return cid, sid, hashes


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

    rankings = get_rankings(db, cid).items
    assert len(rankings) == 2
    winner = next(r for r in rankings if r.image.content_hash == hashes[0])
    loser = next(r for r in rankings if r.image.content_hash == hashes[1])
    assert winner.score > 1500.0
    assert loser.score < 1500.0


def test_elo_calculation_correctness(db: sqlite3.Connection) -> None:
    """K=32, both start at 1500. Expected: 0.5 each. Winner gets +16, loser -16."""
    cid, hashes = _seed_collection_with_images(db, n=2)
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])

    rankings = get_rankings(db, cid).items
    winner = next(r for r in rankings if r.image.content_hash == hashes[0])
    loser = next(r for r in rankings if r.image.content_hash == hashes[1])
    assert abs(winner.score - 1516.0) < 0.01
    assert abs(loser.score - 1484.0) < 0.01


def test_get_rankings_ordered_by_score_desc(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=3)
    # Make hash_0 win twice
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[1])
    record_vote(db, cid, winner_hash=hashes[0], loser_hash=hashes[2])

    rankings = get_rankings(db, cid).items
    assert rankings[0].image.content_hash == hashes[0]
    scores = [r.score for r in rankings]
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

    rankings = get_rankings(db, cid).items
    for r in rankings:
        assert r.matches == 2


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



def _set_standing(
    conn: sqlite3.Connection, cid: int, content_hash: str, *, score: float, matches: int
) -> None:
    conn.execute(
        "INSERT INTO elo_scores (content_hash, collection_id, score, matches) VALUES (?, ?, ?, ?)",
        (content_hash, cid, score, matches),
    )
    conn.commit()


def test_get_pair_always_includes_an_image_with_the_fewest_matches(
    db: sqlite3.Connection,
) -> None:
    cid, hashes = _seed_collection_with_images(db, n=20)
    for h in hashes[1:]:
        _set_standing(db, cid, h, score=1500.0, matches=1)

    for _ in range(30):
        left, right = get_pair(db, cid)
        assert hashes[0] in (left.content_hash, right.content_hash)


def test_get_pair_matches_the_opponent_by_score(db: sqlite3.Connection) -> None:
    """The unvoted image (1500) leads every pair; its opponent is near it."""
    cid, hashes = _seed_collection_with_images(db, n=6)
    scores = [1480.0, 1550.0, 2100.0, 900.0, 2500.0]
    for h, score in zip(hashes[1:], scores, strict=True):
        _set_standing(db, cid, h, score=score, matches=1)
    far = set(hashes[3:])

    far_draws = 0
    for _ in range(200):
        left, right = get_pair(db, cid)
        far_draws += bool(far & {left.content_hash, right.content_hash})
    assert far_draws <= 1


def test_get_pair_leaves_out_the_excluded_images(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=6)
    for _ in range(30):
        left, right = get_pair(db, cid, exclude=hashes[:2])
        assert not set(hashes[:2]) & {left.content_hash, right.content_hash}


def test_get_pair_ignores_an_exclusion_that_leaves_too_few(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=3)
    left, right = get_pair(db, cid, exclude=hashes[:2])
    assert left.content_hash != right.content_hash


# --- Source preset and filter tests ---


def test_get_pair_source_preset(db: sqlite3.Connection) -> None:
    """Source preset collections (no collection_images rows) work via source_id."""
    cid, sid, hashes = _seed_source_preset(db, n=5)
    left, right = get_pair(db, cid, source_id=sid)
    assert left.content_hash != right.content_hash
    assert left.content_hash in hashes
    assert right.content_hash in hashes


def test_get_pair_source_preset_requires_minimum_two(db: sqlite3.Connection) -> None:
    cid, sid, _ = _seed_source_preset(db, n=1)
    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid, source_id=sid)


def test_get_pair_date_filter_restricts_candidates(db: sqlite3.Connection) -> None:
    """date_from / date_to filter the image pool before picking a pair."""
    dates = [
        "2024-01-01T00:00:00",
        "2024-01-02T00:00:00",
        "2024-06-01T00:00:00",
        "2024-06-02T00:00:00",
        "2024-12-01T00:00:00",
    ]
    cid, sid, hashes = _seed_source_preset(db, n=5, dates=dates)

    # Only the first two images fall in January
    for _ in range(20):
        left, right = get_pair(
            db, cid, source_id=sid,
            date_from="2024-01-01", date_to="2024-01-31",
        )
        assert left.content_hash in hashes[:2]
        assert right.content_hash in hashes[:2]


def test_get_pair_date_filter_insufficient_raises(db: sqlite3.Connection) -> None:
    """Filters that leave fewer than 2 images raise ValueError."""
    dates = ["2024-01-01T00:00:00", "2024-06-01T00:00:00", "2024-12-01T00:00:00"]
    cid, sid, _ = _seed_source_preset(db, n=3, dates=dates)

    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid, source_id=sid, date_from="2024-01-01", date_to="2024-01-31")


def test_get_pair_excludes_nsfw_by_default(db: sqlite3.Connection) -> None:
    """NSFW images are excluded from pair selection when show_nsfw=False."""
    cid, hashes = _seed_collection_with_images(db, n=3)
    # Mark the third image as NSFW
    db.execute("UPDATE images SET nsfw = 1 WHERE content_hash = ?", (hashes[2],))
    db.commit()

    for _ in range(20):
        left, right = get_pair(db, cid)
        assert left.content_hash != hashes[2]
        assert right.content_hash != hashes[2]


def test_get_pair_includes_nsfw_when_requested(db: sqlite3.Connection) -> None:
    """NSFW images appear in the pool when show_nsfw=True."""
    cid, hashes = _seed_collection_with_images(db, n=3)
    db.execute("UPDATE images SET nsfw = 1 WHERE content_hash = ?", (hashes[2],))
    db.commit()

    seen = set()
    for _ in range(50):
        left, right = get_pair(db, cid, show_nsfw=True)
        seen.add(left.content_hash)
        seen.add(right.content_hash)

    assert hashes[2] in seen


def test_get_pair_hides_an_nsfw_collection_s_images(db: sqlite3.Connection) -> None:
    """Hidden NSFW covers members of NSFW collections, as in the gallery: an
    NSFW collection has no pairs until NSFW images are shown."""
    cid, _ = _seed_collection_with_images(db, n=3)
    db.execute("UPDATE collections SET nsfw = 1 WHERE id = ?", (cid,))
    db.commit()

    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid)
    assert get_pair(db, cid, show_nsfw=True)


def test_get_pair_hides_images_from_another_nsfw_collection(db: sqlite3.Connection) -> None:
    cid, hashes = _seed_collection_with_images(db, n=3)
    db.execute("INSERT INTO collections (name, nsfw) VALUES ('Private', 1)")
    db.execute(
        "INSERT INTO collection_images (collection_id, content_hash)"
        " SELECT id, ? FROM collections WHERE name = 'Private'",
        (hashes[2],),
    )
    db.commit()

    for _ in range(20):
        left, right = get_pair(db, cid)
        assert hashes[2] not in (left.content_hash, right.content_hash)


def test_get_pair_hides_an_nsfw_source_preset_s_images(db: sqlite3.Connection) -> None:
    cid, sid, _ = _seed_source_preset(db, n=3)
    db.execute("UPDATE collections SET nsfw = 1 WHERE id = ?", (cid,))
    db.commit()

    with pytest.raises(ValueError, match="at least 2"):
        get_pair(db, cid, source_id=sid)
