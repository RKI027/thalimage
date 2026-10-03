"""Integration tests for the scan service."""

import sqlite3
from pathlib import Path

from PIL import Image

from tests.helpers import requires_ffmpeg
from thalimage.db.engine import connect, migrate
from thalimage.services.scan_service import run_scan


def _setup_source(conn: sqlite3.Connection, path: Path) -> int:
    """Insert a source row and return its id."""
    conn.execute(
        "INSERT INTO sources (path, label, recursive) VALUES (?, ?, ?)",
        (str(path), "test", True),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM sources WHERE path = ?", (str(path),)).fetchone()
    return row["id"]


def test_scan_indexes_images(tmp_path: Path) -> None:
    """Full scan pipeline: discover → hash → metadata → thumbnail → DB."""
    # Setup: images on disk
    img_dir = tmp_path / "photos"
    img_dir.mkdir()
    Image.new("RGB", (100, 80), "red").save(img_dir / "red.png")
    Image.new("RGB", (200, 150), "blue").save(img_dir / "blue.jpg")

    # Setup: DB
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    source_id = _setup_source(conn, img_dir)

    thumb_dir = tmp_path / "thumbs"
    result = run_scan(conn, source_id, thumb_dir)

    assert result.scanned == 2
    assert result.added == 2
    assert result.errors == 0

    # Verify images in DB
    rows = conn.execute("SELECT * FROM images ORDER BY filename").fetchall()
    assert len(rows) == 2

    blue = [r for r in rows if r["filename"] == "blue.jpg"][0]
    assert blue["width"] == 200
    assert blue["height"] == 150
    assert blue["thumb_generated"] == 1
    assert len(blue["content_hash"]) == 64

    red = [r for r in rows if r["filename"] == "red.png"][0]
    assert red["width"] == 100
    assert red["height"] == 80

    # Verify thumbnails exist on disk
    for row in rows:
        h = row["content_hash"]
        thumb = thumb_dir / h[:2] / f"{h}.webp"
        assert thumb.exists()

    conn.close()


def test_scan_skips_unchanged_files(tmp_path: Path) -> None:
    """Second scan should skip files that haven't changed."""
    img_dir = tmp_path / "photos"
    img_dir.mkdir()
    Image.new("RGB", (50, 50), "green").save(img_dir / "g.png")

    conn = connect(tmp_path / "test.db")
    migrate(conn)
    source_id = _setup_source(conn, img_dir)
    thumb_dir = tmp_path / "thumbs"

    r1 = run_scan(conn, source_id, thumb_dir)
    assert r1.added == 1

    r2 = run_scan(conn, source_id, thumb_dir)
    assert r2.scanned == 1
    assert r2.added == 0
    assert r2.skipped == 1

    conn.close()


def test_scan_marks_deleted_files(tmp_path: Path) -> None:
    """Files removed from disk should be marked deleted in DB."""
    img_dir = tmp_path / "photos"
    img_dir.mkdir()
    img_path = img_dir / "temp.png"
    Image.new("RGB", (10, 10), "white").save(img_path)
    # A second file stays: a scan that finds nothing at all is refused.
    Image.new("RGB", (10, 10), "black").save(img_dir / "keep.png")

    conn = connect(tmp_path / "test.db")
    migrate(conn)
    source_id = _setup_source(conn, img_dir)
    thumb_dir = tmp_path / "thumbs"

    run_scan(conn, source_id, thumb_dir)
    assert conn.execute("SELECT COUNT(*) FROM images WHERE deleted=0").fetchone()[0] == 2

    # Remove the file
    img_path.unlink()
    run_scan(conn, source_id, thumb_dir)
    assert conn.execute("SELECT COUNT(*) FROM images WHERE deleted=1").fetchone()[0] == 1

    conn.close()


def test_scan_extracts_metadata(tmp_path: Path) -> None:
    """Metadata should be extracted and stored."""
    img_dir = tmp_path / "photos"
    img_dir.mkdir()
    Image.new("RGB", (30, 20), "cyan").save(img_dir / "c.png")

    conn = connect(tmp_path / "test.db")
    migrate(conn)
    source_id = _setup_source(conn, img_dir)
    thumb_dir = tmp_path / "thumbs"

    run_scan(conn, source_id, thumb_dir)

    meta = conn.execute("SELECT * FROM image_metadata").fetchone()
    assert meta is not None
    assert meta["content_hash"] is not None

    conn.close()


# --- TST-002: changed files, bad files, videos ---


def _scan_setup(tmp_path: Path) -> tuple[sqlite3.Connection, Path, int, Path]:
    img_dir = tmp_path / "photos"
    img_dir.mkdir()
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    return conn, img_dir, _setup_source(conn, img_dir), tmp_path / "thumbs"


def _live(conn: sqlite3.Connection) -> dict[str, str]:
    """relative_path -> content_hash of the live (not deleted) images."""
    return {
        r["relative_path"]: r["content_hash"]
        for r in conn.execute("SELECT relative_path, content_hash FROM images WHERE deleted = 0")
    }


def test_modified_file_replaces_its_old_content(tmp_path: Path) -> None:
    import os

    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    path = img_dir / "edit.png"
    Image.new("RGB", (10, 10), "red").save(path)
    run_scan(conn, source_id, thumbs)
    old_hash = _live(conn)["edit.png"]

    Image.new("RGB", (12, 10), "blue").save(path)
    st = path.stat()
    os.utime(path, (st.st_atime, st.st_mtime + 10))
    result = run_scan(conn, source_id, thumbs)

    assert (result.added, result.skipped) == (1, 0)
    new_hash = _live(conn)["edit.png"]
    assert new_hash != old_hash
    deleted = conn.execute(
        "SELECT deleted FROM images WHERE content_hash = ?", (old_hash,)
    ).fetchone()[0]
    assert deleted == 1
    width = conn.execute("SELECT width FROM images WHERE content_hash = ?", (new_hash,)).fetchone()[0]
    assert width == 12
    conn.close()


def test_corrupt_file_counts_an_error_and_the_scan_goes_on(tmp_path: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    Image.new("RGB", (10, 10), "red").save(img_dir / "good.png")
    (img_dir / "broken.png").write_bytes(b"\x89PNG not really")

    result = run_scan(conn, source_id, thumbs)

    assert (result.scanned, result.added, result.errors) == (2, 1, 1)
    assert set(_live(conn)) == {"good.png"}
    conn.close()


@requires_ffmpeg
def test_video_is_indexed_with_a_thumbnail(tmp_path: Path, sample_mp4: Path) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    sample_mp4.rename(img_dir / "clip.mp4")

    result = run_scan(conn, source_id, thumbs)

    assert (result.added, result.errors) == (1, 0)
    row = conn.execute("SELECT * FROM images").fetchone()
    assert (row["width"], row["height"], row["format"]) == (64, 48, "MP4")
    assert (thumbs / row["content_hash"][:2] / f"{row['content_hash']}.webp").exists()
    assert conn.execute("SELECT COUNT(*) FROM image_metadata").fetchone()[0] == 1
    conn.close()


def test_video_without_ffmpeg_is_skipped_as_an_error(tmp_path: Path, monkeypatch) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    (img_dir / "clip.mp4").write_bytes(b"whatever")
    Image.new("RGB", (10, 10), "red").save(img_dir / "pic.png")
    monkeypatch.setattr("thalimage.services.scan_service.ffmpeg_available", lambda: False)

    result = run_scan(conn, source_id, thumbs)

    assert (result.added, result.errors) == (1, 1)
    assert set(_live(conn)) == {"pic.png"}
    conn.close()


# --- GEN-001: the scan never holds the write lock while it works ---


def test_other_connections_can_write_while_a_scan_runs(tmp_path: Path, monkeypatch) -> None:
    # Small batches, so writes happen mid-scan and are checked too.
    monkeypatch.setattr("thalimage.services.scan_service.BATCH_FILES", 2)
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    for i in range(5):
        Image.new("RGB", (10 + i, 10), "red").save(img_dir / f"{i}.png")
    other = connect(tmp_path / "test.db")
    other.execute("PRAGMA busy_timeout = 0")  # fail at once if locked
    writes: list[int] = []

    def on_progress(**kw: object) -> None:
        if kw.get("current"):
            other.execute(
                "INSERT INTO settings (key, value) VALUES (?, 'x')", (f"k{kw['current']}",)
            )
            other.commit()
            writes.append(int(kw["current"]))  # type: ignore[call-overload]

    result = run_scan(conn, source_id, thumbs, progress_callback=on_progress)

    assert result.added == 5
    assert writes == [1, 2, 3, 4, 5]
    other.close()
    conn.close()


# --- GEN-007: an unreachable source fails instead of deleting its images ---


def test_missing_source_folder_fails_and_deletes_nothing(tmp_path: Path) -> None:
    import shutil

    import pytest

    from thalimage.core.scanner import SourceUnavailable

    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    Image.new("RGB", (10, 10), "red").save(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    shutil.rmtree(img_dir)

    with pytest.raises(SourceUnavailable):
        run_scan(conn, source_id, thumbs)
    assert conn.execute("SELECT COUNT(*) FROM images WHERE deleted = 1").fetchone()[0] == 0
    conn.close()


def test_emptied_source_folder_fails_and_deletes_nothing(tmp_path: Path) -> None:
    """An unmounted share often leaves its mount point behind as an empty
    directory: that must not read as "every file was deleted"."""
    import pytest

    from thalimage.core.scanner import SourceUnavailable

    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    Image.new("RGB", (10, 10), "red").save(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    (img_dir / "a.png").unlink()

    with pytest.raises(SourceUnavailable, match="mounted"):
        run_scan(conn, source_id, thumbs)
    assert conn.execute("SELECT COUNT(*) FROM images WHERE deleted = 1").fetchone()[0] == 0
    conn.close()


def test_unreadable_subfolder_keeps_its_images(tmp_path: Path, monkeypatch) -> None:
    import os

    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    (img_dir / "sub").mkdir()
    Image.new("RGB", (10, 10), "red").save(img_dir / "top.png")
    Image.new("RGB", (11, 10), "blue").save(img_dir / "sub" / "deep.png")
    run_scan(conn, source_id, thumbs)

    real_scandir = os.scandir

    def scandir(path: object = ".") -> object:
        if Path(str(path)) == img_dir / "sub":
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "scandir", scandir)
    run_scan(conn, source_id, thumbs)

    assert set(_live(conn)) == {"top.png", str(Path("sub") / "deep.png")}
    conn.close()


def test_unreadable_file_keeps_its_image(tmp_path: Path, monkeypatch) -> None:
    conn, img_dir, source_id, thumbs = _scan_setup(tmp_path)
    Image.new("RGB", (10, 10), "red").save(img_dir / "a.png")
    run_scan(conn, source_id, thumbs)
    # Touch it so the scan re-reads it, then make reading fail.
    import os

    st = (img_dir / "a.png").stat()
    os.utime(img_dir / "a.png", (st.st_atime, st.st_mtime + 5))

    def boom(path: Path) -> str:
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr("thalimage.services.scan_service.content_hash", boom)
    result = run_scan(conn, source_id, thumbs)

    assert result.errors == 1
    assert set(_live(conn)) == {"a.png"}
    conn.close()
