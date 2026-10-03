"""Display-sized preview generation (WebP).

Previews sit between the 400px thumbnail and the original file: large
enough to fill a screen, small enough to send over a slow link. They are
generated on first request and cached on disk, one file per size bucket.
"""

from bisect import bisect_left
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from thalimage.core.webp import write_webp

PREVIEW_SIZES: tuple[int, ...] = (1280, 1920, 2560)

QUALITY = 82


def preview_path(preview_dir: Path, content_hash: str, size: int) -> Path:
    """Compute the on-disk path: {dir}/{size}/{hash[:2]}/{hash}.webp."""
    return preview_dir / str(size) / content_hash[:2] / f"{content_hash}.webp"


def nearest_size(requested: int) -> int:
    """Snap a requested long edge up to the smallest bucket that covers it."""
    i = bisect_left(PREVIEW_SIZES, requested)
    if i >= len(PREVIEW_SIZES):
        return PREVIEW_SIZES[-1]
    return PREVIEW_SIZES[i]


def generate_preview(
    image_path: Path,
    preview_dir: Path,
    content_hash: str,
    size: int,
    *,
    quality: int = QUALITY,
) -> Path:
    """Generate a WebP preview capped at `size` on the long edge.

    Never upscales: a source smaller than the bucket is re-encoded at its
    own dimensions. Skips generation if the file already exists.

    Raises ValueError if the source is not a still image.
    """
    dest = preview_path(preview_dir, content_hash, size)
    if dest.exists():
        return dest

    try:
        with Image.open(image_path) as opened:
            opened.load()
            img = opened.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Cannot generate a preview for {image_path}") from exc

    return write_webp(img, dest, max_size=size, quality=quality)
