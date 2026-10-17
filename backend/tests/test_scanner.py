"""Tests for image scanner."""

import os
from pathlib import Path

import pytest

from thalimage.core.scanner import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SourceUnavailable,
    scan_directory,
)


def test_image_extensions_include_common_formats() -> None:
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS


def test_supported_extensions_include_video() -> None:
    assert ".mp4" in SUPPORTED_EXTENSIONS
    assert ".mov" in SUPPORTED_EXTENSIONS
    assert ".webm" in SUPPORTED_EXTENSIONS
    assert ".avi" in SUPPORTED_EXTENSIONS


def test_scan_finds_images_recursively(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True).files
    filenames = {r.name for r in results}
    assert filenames == {"a.png", "b.jpg", "c.png"}


def test_scan_non_recursive(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=False).files
    filenames = {r.name for r in results}
    assert filenames == {"a.png", "b.jpg"}


def test_scan_ignores_non_image_files(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True).files
    names = {r.name for r in results}
    assert "readme.txt" not in names


@pytest.mark.parametrize("recursive", [True, False])
def test_scan_lists_the_other_files_apart(image_dir: Path, recursive: bool) -> None:
    (image_dir / "sub" / "c.txt").write_text("steps: 20")

    listing = scan_directory(image_dir, recursive=recursive)

    expected = [image_dir / "readme.txt"] + ([image_dir / "sub" / "c.txt"] if recursive else [])
    assert listing.others == expected


@pytest.mark.parametrize("recursive", [True, False])
def test_scan_skips_system_files(image_dir: Path, recursive: bool) -> None:
    for name in (".DS_Store", "._a.png", "Thumbs.db", "thumbs.db@SynoEAStream", "Desktop.ini"):
        (image_dir / name).write_bytes(b"x")

    listing = scan_directory(image_dir, recursive=recursive)

    assert {p.name for p in listing.files} >= {"a.png", "b.jpg"}
    assert "._a.png" not in {p.name for p in listing.files}
    assert listing.others == [image_dir / "readme.txt"]


def test_scan_skips_system_folders(image_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for folder in ("@eaDir/a.png", "#recycle", ".Trashes"):
        (image_dir / folder).mkdir(parents=True)
        (image_dir / folder / "SYNOPHOTO_THUMB_XL.jpg").write_bytes(b"x")
    _deny(monkeypatch, image_dir / "#recycle")

    listing = scan_directory(image_dir, recursive=True)

    assert {p.name for p in listing.files} == {"a.png", "b.jpg", "c.png"}
    assert listing.unreadable == []


def test_scan_empty_directory(tmp_path: Path) -> None:
    listing = scan_directory(tmp_path, recursive=True)
    assert listing.files == []
    assert listing.unreadable == []


@pytest.mark.parametrize("recursive", [True, False])
def test_scan_nonexistent_directory_raises(recursive: bool) -> None:
    with pytest.raises(SourceUnavailable):
        scan_directory(Path("/nonexistent"), recursive=recursive)


def test_scan_a_file_instead_of_a_directory_raises(tmp_path: Path) -> None:
    f = tmp_path / "f.png"
    f.write_bytes(b"x")
    with pytest.raises(SourceUnavailable):
        scan_directory(f)


def _deny(monkeypatch: pytest.MonkeyPatch, denied: Path) -> None:
    """Make listing `denied` fail as an unreadable directory would (works
    as root too, unlike chmod). os.walk lists directories via os.scandir."""
    real_scandir = os.scandir

    def scandir(path: object = ".") -> object:
        if Path(str(path)) == denied:
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "scandir", scandir)


@pytest.mark.parametrize("recursive", [True, False])
def test_scan_unreadable_root_raises(
    image_dir: Path, monkeypatch: pytest.MonkeyPatch, recursive: bool
) -> None:
    _deny(monkeypatch, image_dir)
    with pytest.raises(SourceUnavailable):
        scan_directory(image_dir, recursive=recursive)


def test_scan_reports_unreadable_subdirectories(
    image_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _deny(monkeypatch, image_dir / "sub")
    listing = scan_directory(image_dir, recursive=True)
    assert {p.name for p in listing.files} == {"a.png", "b.jpg"}
    assert listing.unreadable == [image_dir / "sub"]


def test_scan_returns_sorted_paths(image_dir: Path) -> None:
    results = scan_directory(image_dir, recursive=True).files
    assert results == sorted(results)
