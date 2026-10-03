"""Video file handling: thumbnail extraction and metadata via ffmpeg."""

import json
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

from thalimage.core.thumbnails import THUMB_QUALITY, THUMB_SIZE, thumbnail_path
from thalimage.core.webp import write_webp

VIDEO_EXTENSIONS: set[str] = {".mp4", ".mov", ".webm", ".avi"}


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


@lru_cache
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def extract_video_info(file_path: Path) -> dict[str, Any]:
    """Extract width, height, and duration from a video file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {result.stderr}")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError(f"No video stream found in {file_path}")

    stream = streams[0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(stream.get("duration", 0)),
        "codec": stream.get("codec_name", "unknown"),
    }


def extract_video_thumbnail(
    file_path: Path,
    thumb_dir: Path,
    content_hash: str,
    *,
    max_size: int = THUMB_SIZE,
) -> Path:
    """Extract a representative frame from a video and save as WebP thumbnail."""
    out_path = thumbnail_path(thumb_dir, content_hash)
    if out_path.exists():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract a frame at 10% into the video (avoids black intro frames)
    fd, tmp_name = tempfile.mkstemp(dir=out_path.parent, suffix=".frame.png")
    os.close(fd)
    tmp_frame = Path(tmp_name)
    try:
        info = extract_video_info(file_path)
        duration = info.get("duration", 0)
        seek_time = str(max(0.1, duration * 0.1)) if duration > 1 else "0"

        subprocess.run(
            [
                "ffmpeg",
                "-ss", seek_time,
                "-i", str(file_path),
                "-frames:v", "1",
                "-y",
                str(tmp_frame),
            ],
            capture_output=True,
            timeout=30,
        )

        if tmp_frame.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg failed to extract frame from {file_path}")

        with Image.open(tmp_frame) as img:
            img.load()
            write_webp(img, out_path, max_size=max_size, quality=THUMB_QUALITY)
    finally:
        tmp_frame.unlink(missing_ok=True)

    return out_path
