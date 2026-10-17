"""Metadata kept per file version: each file holding an image keeps its
own, and keeps it after the file is gone (#107)."""

from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from tests.test_identity_upgrade import Library
from tests.test_scan_service import _tagged_jpeg
from thalimage.core.hasher import content_hash
from thalimage.core.picture_hash import picture_hash
from thalimage.services.image_service import ImageDetail, get_image
from thalimage.services.tag_service import get_image_tags, remove_image_tag


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(tmp_path)


def _generated(path: Path, prompt: str, *, comment: str = "") -> Path:
    """The same picture every time, with an A1111 prompt (and optionally a
    comment) in its PNG text."""
    info = PngImagePlugin.PngInfo()
    info.add_text("parameters", f"{prompt}\nSteps: 20, Sampler: Euler a, Seed: 1")
    if comment:
        info.add_text("Comment", comment)
    Image.new("RGB", (8, 8), "teal").save(path, pnginfo=info)
    return path


def _detail(library: Library, path: Path) -> ImageDetail:
    detail = get_image(library.conn, picture_hash(path))
    assert detail is not None
    return detail


def test_each_file_keeps_its_own_metadata(library: Library) -> None:
    first = _generated(library.folder / "a.png", "a lighthouse")
    _generated(library.folder / "b.png", "a lighthouse at dusk")
    library.scan()

    detail = _detail(library, first)
    assert detail.prompt == "a lighthouse"
    assert detail.other_versions == 1


def test_copies_with_the_same_ai_parameters_are_not_counted(library: Library) -> None:
    first = _generated(library.folder / "a.png", "a lighthouse")
    _generated(library.folder / "b.png", "a lighthouse", comment="tagged in another tool")
    library.scan()

    assert _detail(library, first).other_versions == 0


def test_a_removed_file_keeps_its_metadata(library: Library) -> None:
    first = _generated(library.folder / "a.png", "a lighthouse")
    second = _generated(library.folder / "b.png", "a lighthouse at dusk")
    library.scan()
    first.unlink()
    library.scan()

    detail = _detail(library, second)
    assert detail.prompt == "a lighthouse at dusk"
    assert detail.other_versions == 1


def test_merging_on_upgrade_keeps_both_files_metadata(
    library: Library, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _generated(library.folder / "a.png", "a lighthouse")
    _generated(library.folder / "b.png", "a lighthouse at dusk")
    library.scan_before_upgrade(monkeypatch)
    assert content_hash(first) in library.live().values()

    library.scan()

    assert _detail(library, first).other_versions == 1


def test_a_removed_tag_is_not_imported_again_from_another_file(library: Library) -> None:
    _tagged_jpeg(library.folder / "a.jpg", "beach")
    library.scan()
    (key,) = set(library.live().values())
    (beach,) = get_image_tags(library.conn, key)
    remove_image_tag(library.conn, key, beach.id)

    _tagged_jpeg(library.folder / "b.jpg", "beach", "sunset")
    library.scan()

    assert set(library.live().values()) == {key}
    assert library.tags(key) == {"sunset"}


def test_a_file_keeps_the_first_name_it_was_scanned_under(library: Library) -> None:
    first = _generated(library.folder / "a.png", "a lighthouse")
    library.scan()
    renamed = first.rename(library.folder / "lighthouse.png")
    library.scan()

    detail = _detail(library, renamed)
    assert detail.filename == "lighthouse.png"
    assert detail.original_name == "a.png"
