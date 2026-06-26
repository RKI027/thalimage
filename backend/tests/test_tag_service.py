"""Tests for tag CRUD and image tagging."""

import sqlite3

import pytest

from thalimage.services.tag_service import (
    add_image_tag,
    create_tag,
    delete_tag,
    get_image_tags,
    get_tag,
    list_tags,
    remove_image_tag,
    update_tag,
)


def _seed_image(conn: sqlite3.Connection, hash_: str = "abc123") -> str:
    conn.execute(
        "INSERT OR IGNORE INTO sources (path, label, recursive) VALUES (?, ?, ?)",
        ("/test", "test", True),
    )
    conn.execute(
        """INSERT INTO images
           (content_hash, filename, source_id, relative_path,
            file_size, width, height, aspect_ratio, format,
            file_modified, thumb_generated)
           VALUES (?, ?, 1, ?, 1000, 100, 100, 1.0, 'PNG', '2024-01-01T00:00:00', 0)
        """,
        (hash_, f"{hash_}.png", f"{hash_}.png"),
    )
    conn.commit()
    return hash_


# --- Tag CRUD ---


def test_create_tag(db: sqlite3.Connection) -> None:
    tag = create_tag(db, "landscape")
    assert tag.id is not None
    assert tag.name == "landscape"
    assert tag.nsfw is False


def test_create_tag_nsfw(db: sqlite3.Connection) -> None:
    tag = create_tag(db, "adult", nsfw=True)
    assert tag.nsfw is True


def test_create_tag_duplicate_raises(db: sqlite3.Connection) -> None:
    create_tag(db, "landscape")
    with pytest.raises(sqlite3.IntegrityError):
        create_tag(db, "landscape")


def test_get_tag(db: sqlite3.Connection) -> None:
    created = create_tag(db, "portrait")
    fetched = get_tag(db, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "portrait"


def test_get_tag_missing_returns_none(db: sqlite3.Connection) -> None:
    assert get_tag(db, 9999) is None


def test_list_tags_empty(db: sqlite3.Connection) -> None:
    assert list_tags(db) == []


def test_list_tags_all(db: sqlite3.Connection) -> None:
    create_tag(db, "alpha")
    create_tag(db, "beta")
    tags = list_tags(db)
    names = [t.name for t in tags]
    assert "alpha" in names
    assert "beta" in names


def test_list_tags_search(db: sqlite3.Connection) -> None:
    create_tag(db, "landscape")
    create_tag(db, "portrait")
    create_tag(db, "wide-angle")
    results = list_tags(db, search="land")
    assert len(results) == 1
    assert results[0].name == "landscape"


def test_list_tags_search_case_insensitive(db: sqlite3.Connection) -> None:
    create_tag(db, "Landscape")
    results = list_tags(db, search="land")
    assert len(results) == 1


def test_update_tag_name(db: sqlite3.Connection) -> None:
    tag = create_tag(db, "old-name")
    updated = update_tag(db, tag.id, name="new-name")
    assert updated is not None
    assert updated.name == "new-name"
    assert updated.nsfw is False


def test_update_tag_nsfw_flag(db: sqlite3.Connection) -> None:
    tag = create_tag(db, "safe", nsfw=False)
    updated = update_tag(db, tag.id, nsfw=True)
    assert updated is not None
    assert updated.nsfw is True


def test_update_tag_missing_returns_none(db: sqlite3.Connection) -> None:
    assert update_tag(db, 9999, name="x") is None


def test_delete_tag(db: sqlite3.Connection) -> None:
    tag = create_tag(db, "to-delete")
    assert delete_tag(db, tag.id) is True
    assert get_tag(db, tag.id) is None


def test_delete_tag_missing_returns_false(db: sqlite3.Connection) -> None:
    assert delete_tag(db, 9999) is False


# --- Image tagging ---


def test_add_and_get_image_tags(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    tag = create_tag(db, "nature")
    add_image_tag(db, hash_, tag.id)
    tags = get_image_tags(db, hash_)
    assert len(tags) == 1
    assert tags[0].name == "nature"


def test_get_image_tags_empty(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    assert get_image_tags(db, hash_) == []


def test_add_image_tag_duplicate_is_idempotent(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    tag = create_tag(db, "nature")
    add_image_tag(db, hash_, tag.id)
    add_image_tag(db, hash_, tag.id)  # second add must not raise
    assert len(get_image_tags(db, hash_)) == 1


def test_remove_image_tag(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    tag = create_tag(db, "nature")
    add_image_tag(db, hash_, tag.id)
    assert remove_image_tag(db, hash_, tag.id) is True
    assert get_image_tags(db, hash_) == []


def test_remove_image_tag_missing_returns_false(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    assert remove_image_tag(db, hash_, 9999) is False


def test_delete_tag_cascades_to_image_tags(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    tag = create_tag(db, "nature")
    add_image_tag(db, hash_, tag.id)
    delete_tag(db, tag.id)
    assert get_image_tags(db, hash_) == []


def test_delete_image_cascades_to_image_tags(db: sqlite3.Connection) -> None:
    hash_ = _seed_image(db)
    tag = create_tag(db, "nature")
    add_image_tag(db, hash_, tag.id)
    db.execute("DELETE FROM images WHERE content_hash = ?", (hash_,))
    db.commit()
    row = db.execute(
        "SELECT COUNT(*) FROM image_tags WHERE image_hash = ?", (hash_,)
    ).fetchone()[0]
    assert row == 0


# --- list_images tag filter ---


def test_list_images_tag_filter(db: sqlite3.Connection) -> None:
    """list_images with tags= returns only images carrying all specified tags."""
    from thalimage.services.image_service import list_images

    h1 = _seed_image(db, "h001")
    h2 = _seed_image(db, "h002")
    _seed_image(db, "h003")

    t1 = create_tag(db, "nature")
    t2 = create_tag(db, "portrait")
    add_image_tag(db, h1, t1.id)
    add_image_tag(db, h1, t2.id)
    add_image_tag(db, h2, t1.id)

    # Filter by single tag "nature" → h1 and h2
    page = list_images(db, tags=["nature"])
    hashes = {i.content_hash for i in page.items}
    assert h1 in hashes
    assert h2 in hashes
    assert "h003" not in hashes

    # Filter by both tags → only h1
    page2 = list_images(db, tags=["nature", "portrait"])
    hashes2 = {i.content_hash for i in page2.items}
    assert hashes2 == {h1}


def test_list_images_no_tag_filter_returns_all(db: sqlite3.Connection) -> None:
    from thalimage.services.image_service import list_images

    _seed_image(db, "x001")
    _seed_image(db, "x002")
    page = list_images(db)
    assert page.total_count == 2
