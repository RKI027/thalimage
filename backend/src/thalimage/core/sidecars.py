"""Sidecars: the files that accompany a media file.

A sidecar is a non-media file in the same folder named after the media
file, either by its stem ("img.png" -> "img.txt") or by its whole name
("img.png" -> "img.png.json"). Generation tools write them: Forge's
parameter .txt, ComfyUI's workflow .json.
"""

import hashlib
from pathlib import Path

from thalimage.core.scanner import SUPPORTED_EXTENSIONS


def _is_media(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def sidecars_of(media: Path) -> list[Path]:
    """The media file's sidecars, by name; none if its folder cannot be read."""
    try:
        entries = list(media.parent.iterdir())
    except OSError:
        return []
    return sorted(
        (
            p for p in entries
            if p.stem in (media.stem, media.name) and not _is_media(p) and p.is_file()
        ),
        key=lambda p: p.name,
    )


def claimed(sidecar: Path) -> bool:
    """Whether a media file in the sidecar's folder still names it."""
    try:
        entries = list(sidecar.parent.iterdir())
    except OSError:
        return True
    return any(_is_media(p) and sidecar.stem in (p.stem, p.name) for p in entries)


def digest(path: Path) -> str:
    """SHA-256 of the file's content, to tell sidecars of copies apart."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()
