"""The picture hash: an image's identity, left unchanged by metadata edits.

The fixtures come from `fixtures/picture_hash/make.sh`: each picture, the
same file after ExifTool wrote keywords, a rating and a comment into it,
and a different picture.
"""

from pathlib import Path

import pytest
from PIL import Image

from thalimage.core.hasher import content_hash
from thalimage.core.picture_hash import picture_hash

FIXTURES = Path(__file__).parent / "fixtures" / "picture_hash"

HASHED = [
    "picture.png",
    "picture.jpg",
    "progressive.jpg",
    "picture.webp",
    "picture.tiff",
    "picture.avif",
    "clip.mp4",
    "clip.mov",
]


def _variant(name: str, suffix: str) -> Path:
    stem, ext = name.rsplit(".", 1)
    return FIXTURES / f"{stem}-{suffix}.{ext}"


@pytest.mark.parametrize("name", HASHED)
def test_writing_metadata_keeps_the_picture_hash(name: str) -> None:
    original, tagged = FIXTURES / name, _variant(name, "tagged")
    assert content_hash(original) != content_hash(tagged)
    assert picture_hash(original) == picture_hash(tagged)


@pytest.mark.parametrize("name", HASHED)
def test_a_different_picture_has_a_different_hash(name: str) -> None:
    assert picture_hash(FIXTURES / name) != picture_hash(_variant(name, "other"))


@pytest.mark.parametrize("name", HASHED)
def test_the_picture_hash_is_not_the_file_hash(name: str) -> None:
    path = FIXTURES / name
    assert picture_hash(path) != content_hash(path)


@pytest.mark.parametrize("ext", ["gif", "bmp"])
def test_other_formats_fall_back_to_the_file_hash(tmp_path: Path, ext: str) -> None:
    path = tmp_path / f"a.{ext}"
    Image.new("RGB", (8, 8), "red").save(path)
    assert picture_hash(path) == content_hash(path)


@pytest.mark.parametrize("name", HASHED)
def test_a_truncated_file_falls_back_to_the_file_hash(tmp_path: Path, name: str) -> None:
    data = (FIXTURES / name).read_bytes()
    path = tmp_path / name
    path.write_bytes(data[: len(data) // 3])
    assert picture_hash(path) == content_hash(path)
