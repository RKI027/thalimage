"""Tests for file-based thumbnail generation."""

from pathlib import Path

from PIL import Image

from thalimage.core.thumbnails import (
    generate_thumbnail,
    thumbnail_path,
    generate_thumbnails_parallel,
)


def test_thumbnail_path_uses_hash_prefix() -> None:
    base = Path("/cache/thumbs")
    h = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    result = thumbnail_path(base, h)
    assert result == base / "ab" / f"{h}.webp"


def test_generate_thumbnail_creates_webp(sample_png: Path, tmp_path: Path) -> None:
    thumb_dir = tmp_path / "thumbs"
    h = "aabbcc"
    path = generate_thumbnail(sample_png, thumb_dir, h)
    assert path.exists()
    assert path.suffix == ".webp"
    with Image.open(path) as img:
        assert img.format == "WEBP"


def test_generate_thumbnail_respects_max_size(tmp_path: Path) -> None:
    """Large image should be scaled down to max_size."""
    img = Image.new("RGB", (1000, 500), "green")
    src = tmp_path / "big.png"
    img.save(src)

    thumb_dir = tmp_path / "thumbs"
    path = generate_thumbnail(src, thumb_dir, "deadbeef", max_size=200)
    with Image.open(path) as thumb:
        assert max(thumb.width, thumb.height) <= 200


def test_generate_thumbnail_preserves_aspect_ratio(tmp_path: Path) -> None:
    img = Image.new("RGB", (400, 200), "green")
    src = tmp_path / "wide.png"
    img.save(src)

    thumb_dir = tmp_path / "thumbs"
    path = generate_thumbnail(src, thumb_dir, "beef", max_size=100)
    with Image.open(path) as thumb:
        ratio = thumb.width / thumb.height
        assert abs(ratio - 2.0) < 0.1


def test_generate_thumbnail_skips_existing(sample_png: Path, tmp_path: Path) -> None:
    thumb_dir = tmp_path / "thumbs"
    p1 = generate_thumbnail(sample_png, thumb_dir, "hash1")
    mtime1 = p1.stat().st_mtime
    p2 = generate_thumbnail(sample_png, thumb_dir, "hash1")
    assert p1 == p2
    assert p2.stat().st_mtime == mtime1


def test_generate_thumbnails_parallel(image_dir: Path, tmp_path: Path) -> None:
    thumb_dir = tmp_path / "thumbs"
    items = [
        (image_dir / "a.png", "hash_a"),
        (image_dir / "b.jpg", "hash_b"),
        (image_dir / "sub" / "c.png", "hash_c"),
    ]
    results = generate_thumbnails_parallel(items, thumb_dir)
    assert len(results) == 3
    for path in results:
        assert path.exists()
