"""Tests for video thumbnail extraction and metadata."""

from pathlib import Path
from unittest.mock import patch

import pytest

from thalimage.core.video import (
    VIDEO_EXTENSIONS,
    extract_video_info,
    extract_video_thumbnail,
    ffmpeg_available,
    is_video,
)


def test_is_video_positive():
    for ext in VIDEO_EXTENSIONS:
        assert is_video(Path(f"test{ext}"))
        assert is_video(Path(f"test{ext.upper()}"))


def test_is_video_negative():
    assert not is_video(Path("test.png"))
    assert not is_video(Path("test.jpg"))
    assert not is_video(Path("test.txt"))


def test_ffmpeg_available_with_ffmpeg():
    with patch("thalimage.core.video.shutil.which", return_value="/usr/bin/ffmpeg"):
        # Clear lru_cache
        ffmpeg_available.cache_clear()
        assert ffmpeg_available() is True
    ffmpeg_available.cache_clear()


def test_ffmpeg_available_without_ffmpeg():
    with patch("thalimage.core.video.shutil.which", return_value=None):
        ffmpeg_available.cache_clear()
        assert ffmpeg_available() is False
    ffmpeg_available.cache_clear()


# Integration tests that require ffmpeg
requires_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available(), reason="ffmpeg not available"
)


@pytest.fixture
def sample_mp4(tmp_path: Path) -> Path:
    """Create a tiny MP4 video using ffmpeg."""
    out = tmp_path / "test.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=red:s=64x48:d=1",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=30,
    )
    assert out.exists(), "Failed to create test MP4"
    return out


@requires_ffmpeg
def test_extract_video_info(sample_mp4: Path):
    info = extract_video_info(sample_mp4)
    assert info["width"] == 64
    assert info["height"] == 48
    assert info["duration"] > 0
    assert "codec" in info


@requires_ffmpeg
def test_extract_video_thumbnail_creates_webp(sample_mp4: Path, tmp_path: Path):
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    content_hash = "abc123def456"

    out = extract_video_thumbnail(sample_mp4, thumb_dir, content_hash)
    assert out.exists()
    assert out.suffix == ".webp"
    assert out.parent.name == "ab"  # hash[:2] subdirectory


@requires_ffmpeg
def test_extract_video_thumbnail_skips_existing(sample_mp4: Path, tmp_path: Path):
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    content_hash = "abc123def456"

    out1 = extract_video_thumbnail(sample_mp4, thumb_dir, content_hash)
    mtime1 = out1.stat().st_mtime

    out2 = extract_video_thumbnail(sample_mp4, thumb_dir, content_hash)
    assert out1 == out2
    assert out2.stat().st_mtime == mtime1


@requires_ffmpeg
def test_extract_video_info_invalid_file(tmp_path: Path):
    bad_file = tmp_path / "not_a_video.mp4"
    bad_file.write_text("not a video")
    with pytest.raises(RuntimeError):
        extract_video_info(bad_file)
