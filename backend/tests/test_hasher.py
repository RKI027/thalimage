"""Tests for content hasher."""

from pathlib import Path

from thalimage.core.hasher import content_hash


def test_hash_is_hex_sha256(sample_png: Path) -> None:
    h = content_hash(sample_png)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_same_content_same_hash(tmp_path: Path) -> None:
    data = b"identical content"
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(data)
    f2.write_bytes(data)
    assert content_hash(f1) == content_hash(f2)


def test_different_content_different_hash(sample_png: Path, sample_jpeg: Path) -> None:
    assert content_hash(sample_png) != content_hash(sample_jpeg)


def test_hash_deterministic(sample_png: Path) -> None:
    h1 = content_hash(sample_png)
    h2 = content_hash(sample_png)
    assert h1 == h2
