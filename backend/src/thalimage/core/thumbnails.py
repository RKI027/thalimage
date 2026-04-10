"""File-based thumbnail generation (WebP)."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image


def thumbnail_path(thumb_dir: Path, content_hash: str) -> Path:
    """Compute the on-disk path for a thumbnail: {dir}/{hash[:2]}/{hash}.webp."""
    return thumb_dir / content_hash[:2] / f"{content_hash}.webp"


def generate_thumbnail(
    image_path: Path,
    thumb_dir: Path,
    content_hash: str,
    *,
    max_size: int = 400,
    quality: int = 80,
) -> Path:
    """Generate a WebP thumbnail on disk. Skips if it already exists.

    Returns the path to the thumbnail file.
    """
    dest = thumbnail_path(thumb_dir, content_hash)
    if dest.exists():
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        img.save(dest, format="WEBP", quality=quality, method=4)

    return dest


def generate_thumbnails_parallel(
    items: list[tuple[Path, str]],
    thumb_dir: Path,
    *,
    max_size: int = 400,
    max_workers: int | None = None,
) -> list[Path]:
    """Generate thumbnails in parallel.

    items: list of (image_path, content_hash) tuples.
    Returns list of thumbnail paths in the same order.
    """
    def _worker(item: tuple[Path, str]) -> Path:
        return generate_thumbnail(item[0], thumb_dir, item[1], max_size=max_size)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_worker, items))
