"""Tests for display-sized preview generation."""

from pathlib import Path

import pytest
from PIL import Image

from thalimage.core.previews import (
    PREVIEW_SIZES,
    generate_preview,
    nearest_size,
    preview_path,
)


def test_preview_path_separates_sizes_and_uses_hash_prefix() -> None:
    base = Path("/cache/previews")
    h = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    assert preview_path(base, h, 1920) == base / "1920" / "ab" / f"{h}.webp"


def test_nearest_size_snaps_up_to_a_bucket() -> None:
    assert nearest_size(800) == 1280
    assert nearest_size(1280) == 1280
    assert nearest_size(1600) == 1920


def test_nearest_size_clamps_to_the_largest_bucket() -> None:
    assert nearest_size(9999) == max(PREVIEW_SIZES)


def test_generate_preview_caps_the_long_edge(tmp_path: Path) -> None:
    src = tmp_path / "big.png"
    Image.new("RGB", (4000, 2000), "green").save(src)

    path = generate_preview(src, tmp_path / "previews", "deadbeef", 1280)

    with Image.open(path) as preview:
        assert preview.format == "WEBP"
        assert max(preview.width, preview.height) == 1280
        assert preview.height == 640


def test_generate_preview_never_upscales(tmp_path: Path) -> None:
    src = tmp_path / "small.png"
    Image.new("RGB", (300, 200), "red").save(src)

    path = generate_preview(src, tmp_path / "previews", "cafe", 1920)

    with Image.open(path) as preview:
        assert (preview.width, preview.height) == (300, 200)


def test_generate_preview_reuses_an_existing_file(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    Image.new("RGB", (2000, 1000), "blue").save(src)
    previews = tmp_path / "previews"

    first = generate_preview(src, previews, "beef", 1280)
    stamp = first.stat().st_mtime_ns
    second = generate_preview(src, previews, "beef", 1280)

    assert second == first
    assert second.stat().st_mtime_ns == stamp


def test_generate_preview_rejects_a_non_image(tmp_path: Path) -> None:
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"not an image")

    with pytest.raises(ValueError):
        generate_preview(src, tmp_path / "previews", "f00d", 1280)


def test_generate_preview_flattens_transparency(tmp_path: Path) -> None:
    """WebP keeps alpha, but paletted and LA modes must not crash the encoder."""
    src = tmp_path / "p.png"
    Image.new("P", (800, 600)).save(src)

    path = generate_preview(src, tmp_path / "previews", "abcd", 1280)

    assert path.exists()


def test_concurrent_generation_of_one_preview_all_succeed(tmp_path: Path) -> None:
    """GEN-017: the viewer and a prefetch can ask for the same preview at
    once; each request must succeed and leave a complete file behind."""
    import threading

    src = tmp_path / "big.png"
    Image.new("RGB", (3000, 2000), "purple").save(src)
    preview_dir = tmp_path / "previews"
    n = 8
    barrier = threading.Barrier(n)
    errors: list[BaseException] = []

    def worker() -> None:
        barrier.wait()
        try:
            generate_preview(src, preview_dir, "h" * 64, 1280)
        except BaseException as exc:  # noqa: BLE001 - collected for the assert
            errors.append(exc)

    for _ in range(3):
        for p in preview_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        with Image.open(preview_path(preview_dir, "h" * 64, 1280)) as out:
            out.load()
            assert out.size == (1280, 853)
        assert [p.name for p in preview_dir.rglob("*.tmp")] == []
