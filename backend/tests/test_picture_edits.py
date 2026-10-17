"""A picture edited in place: the scan offers to keep it the same image."""

import sqlite3
from pathlib import Path

from PIL import Image

from tests.test_scan_service import _scan_setup
from thalimage.services import user_settings
from thalimage.services.picture_edits import keep_separate, merge, possible_edit_of
from thalimage.services.scan_service import run_scan


def _picture(path: Path, extent: tuple[float, float, float, float] = (-2, -1.5, 1, 1.5)) -> None:
    Image.effect_mandelbrot((256, 256), extent, 100).convert("RGB").save(path)


def _crop(path: Path) -> None:
    """Crop 5% off each side, in place."""
    with Image.open(path) as img:
        cropped = img.crop((6, 6, 250, 250))
    cropped.save(path)


def _key(conn: sqlite3.Connection, relative: str) -> str:
    return conn.execute(
        "SELECT content_hash FROM image_locations WHERE relative_path = ?", (relative,)
    ).fetchone()[0]


def _edited(tmp_path: Path) -> tuple[sqlite3.Connection, Path, int, Path, str, str]:
    """A scanned picture, cropped in place and scanned again: the
    connection, folder, source, thumbs, and the old and new keys."""
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    _picture(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    old = _key(conn, "a.png")
    _crop(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    return conn, img_dir, source_id, thumbs, old, _key(conn, "a.png")


def test_a_picture_edited_in_place_is_offered_as_an_edit(tmp_path: Path) -> None:
    conn, *_, old, new = _edited(tmp_path)

    edit = possible_edit_of(conn, new)

    assert edit is not None
    assert edit.old_hash == old
    assert 0 < edit.distance <= 0.25
    conn.close()


def test_an_unrelated_picture_at_the_same_path_is_not(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    _picture(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    _picture(img_dir / "a.png", (-0.8, 0, -0.4, 0.4))
    run_scan(conn, source_id, thumbs)

    assert possible_edit_of(conn, _key(conn, "a.png")) is None
    conn.close()


def test_an_edit_is_not_offered_while_the_old_picture_has_a_copy(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    _picture(img_dir / "a.png")
    (img_dir / "copy.png").write_bytes((img_dir / "a.png").read_bytes())
    run_scan(conn, source_id, thumbs)
    _crop(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)

    assert possible_edit_of(conn, _key(conn, "a.png")) is None
    conn.close()


def test_the_edit_threshold_setting_decides_what_counts(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    user_settings.write(conn, edit_threshold=0.0)
    _picture(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    _crop(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)

    assert possible_edit_of(conn, _key(conn, "a.png")) is None
    conn.close()


def test_an_edit_is_no_longer_offered_once_the_old_picture_is_back(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs, old, new = _edited(tmp_path)
    _picture(img_dir / "restored.png")
    run_scan(conn, source_id, thumbs)

    assert _key(conn, "restored.png") == old
    assert possible_edit_of(conn, new) is None
    conn.close()


def _tag(conn: sqlite3.Connection, h: str, name: str) -> None:
    tag_id = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,)).lastrowid
    conn.execute("INSERT INTO image_tags (image_hash, tag_id) VALUES (?, ?)", (h, tag_id))
    conn.commit()


def test_merging_carries_the_old_image_over_to_the_edit(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    _picture(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    old = _key(conn, "a.png")
    _tag(conn, old, "beach")
    _crop(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    new = _key(conn, "a.png")

    assert merge(conn, new) == old

    tags = [r[0] for r in conn.execute(
        "SELECT t.name FROM image_tags it JOIN tags t ON t.id = it.tag_id WHERE it.image_hash = ?",
        (new,),
    )]
    assert tags == ["beach"]
    assert conn.execute("SELECT deleted FROM images WHERE content_hash = ?", (new,)).fetchone()[0] == 0
    assert conn.execute("SELECT 1 FROM images WHERE content_hash = ?", (old,)).fetchone() is None
    assert possible_edit_of(conn, new) is None
    conn.close()


def test_merging_keeps_an_earlier_edit_pending_on_the_merged_image(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs, first, second = _edited(tmp_path)
    _crop(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    third = _key(conn, "a.png")

    merge(conn, third)

    edit = possible_edit_of(conn, third)
    assert edit is not None and edit.old_hash == first
    conn.close()


def test_merging_an_image_with_no_possible_edit_does_nothing(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    _picture(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)

    assert merge(conn, _key(conn, "a.png")) is None
    conn.close()


def test_kept_separate_is_not_offered_again(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs, old, new = _edited(tmp_path)

    keep_separate(conn, new)
    assert possible_edit_of(conn, new) is None

    # A later scan reading the file again finds the same pair.
    conn.execute("UPDATE file_metadata SET extractor_version = 0")
    conn.commit()
    run_scan(conn, source_id, thumbs)
    assert possible_edit_of(conn, new) is None
    conn.close()
