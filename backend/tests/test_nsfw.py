"""Tests for NSFW triggers, filters, and settings."""

import sqlite3

from thalimage.services.tag_service import add_image_tag, create_tag
from thalimage.services.image_service import list_images


def _seed_source(conn: sqlite3.Connection) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO sources (path, label, recursive) VALUES (?, ?, ?)",
        ("/test", "test", True),
    )
    conn.commit()
    return conn.execute("SELECT id FROM sources WHERE path = '/test'").fetchone()[0]


def _seed_image(conn: sqlite3.Connection, hash_: str, *, source_id: int = 1) -> str:
    conn.execute(
        """INSERT INTO images
           (content_hash, filename, source_id, relative_path,
            file_size, width, height, aspect_ratio, format,
            file_modified, thumb_generated)
           VALUES (?, ?, ?, ?, 1000, 100, 100, 1.0, 'PNG', '2024-01-01T00:00:00', 0)
        """,
        (hash_, f"{hash_}.png", source_id, f"{hash_}.png"),
    )
    conn.commit()
    return hash_


# --- NSFW trigger: tag-driven auto-flag ---


def test_adding_nsfw_tag_sets_image_nsfw(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    h = _seed_image(db, "img001", source_id=sid)
    tag = create_tag(db, "adult", nsfw=True)
    add_image_tag(db, h, tag.id)

    nsfw_val = db.execute(
        "SELECT nsfw FROM images WHERE content_hash = ?", (h,)
    ).fetchone()[0]
    assert nsfw_val == 1


def test_adding_safe_tag_does_not_set_image_nsfw(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    h = _seed_image(db, "img002", source_id=sid)
    tag = create_tag(db, "nature", nsfw=False)
    add_image_tag(db, h, tag.id)

    nsfw_val = db.execute(
        "SELECT nsfw FROM images WHERE content_hash = ?", (h,)
    ).fetchone()[0]
    assert nsfw_val == 0


def test_removing_nsfw_tag_resets_image_nsfw(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    h = _seed_image(db, "img003", source_id=sid)
    tag = create_tag(db, "adult", nsfw=True)
    add_image_tag(db, h, tag.id)

    from thalimage.services.tag_service import remove_image_tag
    remove_image_tag(db, h, tag.id)

    nsfw_val = db.execute(
        "SELECT nsfw FROM images WHERE content_hash = ?", (h,)
    ).fetchone()[0]
    assert nsfw_val == 0


def test_removing_one_of_two_nsfw_tags_keeps_image_nsfw(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    h = _seed_image(db, "img004", source_id=sid)
    tag1 = create_tag(db, "adult", nsfw=True)
    tag2 = create_tag(db, "explicit", nsfw=True)
    add_image_tag(db, h, tag1.id)
    add_image_tag(db, h, tag2.id)

    from thalimage.services.tag_service import remove_image_tag
    remove_image_tag(db, h, tag1.id)

    nsfw_val = db.execute(
        "SELECT nsfw FROM images WHERE content_hash = ?", (h,)
    ).fetchone()[0]
    assert nsfw_val == 1


def test_removing_safe_tag_does_not_change_nsfw_flag(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    h = _seed_image(db, "img005", source_id=sid)
    nsfw_tag = create_tag(db, "adult", nsfw=True)
    safe_tag = create_tag(db, "nature", nsfw=False)
    add_image_tag(db, h, nsfw_tag.id)
    add_image_tag(db, h, safe_tag.id)

    from thalimage.services.tag_service import remove_image_tag
    remove_image_tag(db, h, safe_tag.id)

    nsfw_val = db.execute(
        "SELECT nsfw FROM images WHERE content_hash = ?", (h,)
    ).fetchone()[0]
    assert nsfw_val == 1


# --- list_images NSFW filter ---


def test_list_images_hides_nsfw_by_default(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    safe_hash = _seed_image(db, "safe01", source_id=sid)
    nsfw_hash = _seed_image(db, "nsfw01", source_id=sid)
    tag = create_tag(db, "adult", nsfw=True)
    add_image_tag(db, nsfw_hash, tag.id)

    page = list_images(db)
    hashes = {i.content_hash for i in page.items}
    assert safe_hash in hashes
    assert nsfw_hash not in hashes


def test_list_images_shows_nsfw_when_requested(db: sqlite3.Connection) -> None:
    sid = _seed_source(db)
    safe_hash = _seed_image(db, "safe02", source_id=sid)
    nsfw_hash = _seed_image(db, "nsfw02", source_id=sid)
    tag = create_tag(db, "adult", nsfw=True)
    add_image_tag(db, nsfw_hash, tag.id)

    page = list_images(db, show_nsfw=True)
    hashes = {i.content_hash for i in page.items}
    assert safe_hash in hashes
    assert nsfw_hash in hashes


# --- Collection NSFW flag ---


def test_collection_nsfw_default_false(db: sqlite3.Connection) -> None:
    db.execute("INSERT INTO collections (name) VALUES (?)", ("Test",))
    db.commit()
    cid = db.execute("SELECT id FROM collections ORDER BY id DESC LIMIT 1").fetchone()[0]
    row = db.execute("SELECT nsfw FROM collections WHERE id = ?", (cid,)).fetchone()
    assert row[0] == 0


def test_collection_nsfw_can_be_set_true(db: sqlite3.Connection) -> None:
    from thalimage.services.collection_service import create_collection, update_collection
    coll = create_collection(db, "NSFW Collection")
    updated = update_collection(db, coll.id, nsfw=True)
    assert updated is not None
    assert not isinstance(updated, str)
    assert updated.nsfw is True


def test_collection_nsfw_update_returns_correct_model(db: sqlite3.Connection) -> None:
    from thalimage.services.collection_service import create_collection, update_collection
    coll = create_collection(db, "Safe Collection")
    assert coll.nsfw is False
    updated = update_collection(db, coll.id, nsfw=True)
    assert updated is not None
    assert not isinstance(updated, str)
    assert updated.nsfw is True
    # Flip back
    updated2 = update_collection(db, coll.id, nsfw=False)
    assert updated2 is not None
    assert not isinstance(updated2, str)
    assert updated2.nsfw is False
