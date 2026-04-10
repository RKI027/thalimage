"""Tests for image scanner."""

from pathlib import Path

from thalimage.core.scanner import scan_directory, IMAGE_EXTENSIONS


def test_image_extensions_include_common_formats() -> None:
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS
    assert ".mp4" in IMAGE_EXTENSIONS


def test_scan_finds_images_recursively(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True)
    filenames = {r.name for r in results}
    assert filenames == {"a.png", "b.jpg", "c.png"}


def test_scan_non_recursive(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=False)
    filenames = {r.name for r in results}
    assert filenames == {"a.png", "b.jpg"}


def test_scan_ignores_non_image_files(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True)
    names = {r.name for r in results}
    assert "readme.txt" not in names


def test_scan_empty_directory(tmp_path: Path) -> None:
    results = scan_directory(tmp_path, recursive=True)
    assert results == []


def test_scan_nonexistent_directory() -> None:
    results = scan_directory(Path("/nonexistent"), recursive=True)
    assert results == []


def test_scan_returns_sorted_paths(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True)
    assert results == sorted(results)
