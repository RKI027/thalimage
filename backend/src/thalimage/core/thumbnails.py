"""File-based thumbnail generation (WebP)."""

from pathlib import Path

from PIL import Image

from thalimage.core.webp import write_webp

THUMB_SIZE = 400
THUMB_QUALITY = 80


def thumbnail_path(thumb_dir: Path, content_hash: str) -> Path:
    """Compute the on-disk path for a thumbnail: {dir}/{hash[:2]}/{hash}.webp."""
    return thumb_dir / content_hash[:2] / f"{content_hash}.webp"


def generate_thumbnail(
    image_path: Path,
    thumb_dir: Path,
    content_hash: str,
    *,
    max_size: int = THUMB_SIZE,
    quality: int = THUMB_QUALITY,
) -> Path:
    """Generate a WebP thumbnail on disk. Skips if it already exists.

    Returns the path to the thumbnail file.
    """
    dest = thumbnail_path(thumb_dir, content_hash)
    if dest.exists():
        return dest

    with Image.open(image_path) as img:
        img.load()
        return write_webp(img, dest, max_size=max_size, quality=quality)

