"""The one WebP writer behind thumbnails, video thumbnails and previews."""

import os
import tempfile
from pathlib import Path

from PIL import Image


def write_webp(img: Image.Image, dest: Path, *, max_size: int, quality: int) -> Path:
    """Shrink `img` in place to fit `max_size` on its long edge (never
    upscaling), then write it to `dest` as WebP.

    The file is written under a temp name unique to this call and renamed
    into place, so concurrent writers of the same `dest` never share a temp
    file and readers never see a half-written one.
    """
    # WebP encodes RGB/RGBA only; P, LA, L and the like must be converted.
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f"{dest.name}.", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        img.save(tmp, format="WEBP", quality=quality, method=4)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest
