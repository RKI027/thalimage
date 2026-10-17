"""Sidecars: the files that accompany a media file.

A sidecar is a non-media file in the same folder named after the media
file, either by its stem ("img.png" -> "img.txt") or by its whole name
("img.png" -> "img.png.json"). Generation tools write them: Forge's
parameter .txt, ComfyUI's workflow .json.
"""

import hashlib
from pathlib import Path

from thalimage.core.scanner import is_media


def sidecars_of(media: Path) -> list[Path]:
    """The media file's sidecars, by name; none if its folder cannot be read."""
    try:
        entries = list(media.parent.iterdir())
    except OSError:
        return []
    return sorted(
        (
            p for p in entries
            if p.stem in (media.stem, media.name) and not is_media(p) and p.is_file()
        ),
        key=lambda p: p.name,
    )


def claimed(sidecar: Path) -> bool:
    """Whether a media file in the sidecar's folder still names it."""
    try:
        entries = list(sidecar.parent.iterdir())
    except OSError:
        return True
    return names_any(sidecar, [p for p in entries if is_media(p)])


def names_any(sidecar: Path, media: list[Path]) -> bool:
    """Whether one of the media files is named the way the sidecar is."""
    return any(sidecar.stem in (p.stem, p.name) for p in media)


def digest(path: Path) -> str:
    """SHA-256 of the file's content, to tell sidecars of copies apart."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


MAX_TEXT_BYTES = 256 * 1024


def text_of(sidecar: Path) -> str | None:
    """The sidecar's text; None when it is over MAX_TEXT_BYTES or not UTF-8."""
    with open(sidecar, "rb") as f:
        data = f.read(MAX_TEXT_BYTES + 1)
    if len(data) > MAX_TEXT_BYTES:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
