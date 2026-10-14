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

VIDEO_EXTENSIONS: set[str] = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


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


# What iOS Safari, and so every iOS browser, plays. A video outside this
# gets a playable copy: its streams are reused where they qualify.
PLAYABLE_CONTAINERS = {".mp4", ".m4v", ".mov"}
PLAYABLE_AUDIO = {"aac", "mp3", "alac"}
PLAYABLE_PIX_FMTS = {"yuv420p", "yuvj420p"}

# Long enough for a full transcode of a long clip on a slow CPU.
COPY_TIMEOUT = 4 * 3600


def probe_streams(file_path: Path) -> list[dict[str, Any]]:
    """Every stream of the file, as ffprobe describes it."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(file_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {result.stderr}")
    streams: list[dict[str, Any]] = json.loads(result.stdout).get("streams", [])
    return streams


def playable_copy_args(ext: str, streams: list[dict[str, Any]]) -> list[str] | None:
    """The ffmpeg codec options that make an MP4 iOS plays from a video
    with this extension and these streams; None if it plays as it is.

    H.264 (8-bit 4:2:0), HEVC and AV1 video are kept, as are AAC, MP3 and
    ALAC audio; anything else is re-encoded to H.264 and AAC. HEVC is
    tagged hvc1, which Safari requires.
    """
    videos = [
        s for s in streams
        if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")
    ]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise ValueError("No video stream")
    video = videos[0]
    codec = video.get("codec_name")

    video_args: list[str]
    if codec == "h264" and video.get("pix_fmt") in PLAYABLE_PIX_FMTS:
        video_args = ["-c:v", "copy"]
    elif codec == "hevc":
        video_args = ["-c:v", "copy"]
        if video.get("codec_tag_string") != "hvc1":
            video_args += ["-tag:v", "hvc1"]
    elif codec == "av1":
        video_args = ["-c:v", "copy"]
    else:
        video_args = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p"]

    audio_args: list[str] = []
    if audios:
        if audios[0].get("codec_name") in PLAYABLE_AUDIO:
            audio_args = ["-c:a", "copy"]
        else:
            audio_args = ["-c:a", "aac", "-b:a", "160k"]

    if (
        ext.lower() in PLAYABLE_CONTAINERS
        and video_args == ["-c:v", "copy"]
        and audio_args in ([], ["-c:a", "copy"])
    ):
        return None
    return video_args + audio_args


def playable_copy_path(video_dir: Path, content_hash: str) -> Path:
    """{dir}/{hash[:2]}/{hash}.mp4"""
    return video_dir / content_hash[:2] / f"{content_hash}.mp4"


def make_playable_copy(source: Path, dest: Path, codec_args: list[str]) -> None:
    """Write an MP4 of the source's first video and audio streams, with
    these codec options, to dest. Written aside and renamed, so a copy
    that exists is complete."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".part.mp4")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y", "-i", str(source),
                "-map", "0:V:0", "-map", "0:a:0?", *codec_args,
                "-movflags", "+faststart", str(tmp),
            ],
            capture_output=True,
            text=True,
            timeout=COPY_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {source}: {result.stderr.strip()}")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
