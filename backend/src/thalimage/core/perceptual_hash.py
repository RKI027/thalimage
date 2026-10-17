"""The perceptual hash: a 64-bit fingerprint of what a picture looks like.

A DCT hash (pHash): the picture in greyscale at 32x32, transformed, keeps
one bit per low frequency, set when that frequency is above their median.
Resizing, re-encoding and colour changes move few bits; cropping moves
more the more is cut. Unlike the picture hash, it decodes the picture:
decoders disagreeing on a few pixels shift it by a bit at most.
"""

import math
from pathlib import Path

from PIL import Image

# Raised when the hash changes, so the next scan computes it again.
PERCEPTUAL_HASH_VERSION = 1

_SIZE = 32  # the side of the greyscale picture transformed
_KEPT = 8  # the lowest frequencies kept, per axis: 64 bits
_BITS = _KEPT * _KEPT

_COSINES = [
    [math.cos(math.pi * (2 * x + 1) * u / (2 * _SIZE)) for x in range(_SIZE)]
    for u in range(_KEPT)
]


def perceptual_hash(path: Path) -> int:
    """The picture's perceptual hash, as a signed 64-bit integer (what
    SQLite stores). Transparent areas count as white."""
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
    flat = Image.new("RGBA", rgba.size, "white")
    flat.alpha_composite(rgba)
    grey = flat.convert("L").resize((_SIZE, _SIZE), Image.Resampling.LANCZOS)
    pixels = grey.tobytes()
    rows = [pixels[y * _SIZE : (y + 1) * _SIZE] for y in range(_SIZE)]
    # The 2D DCT, separably: along the rows, then down the columns.
    across = [[sum(c * p for c, p in zip(cos, row, strict=True)) for cos in _COSINES] for row in rows]
    freqs = [
        sum(c * across[y][u] for y, c in enumerate(cos)) for cos in _COSINES for u in range(_KEPT)
    ]
    median = sorted(freqs)[_BITS // 2]
    bits = sum(1 << i for i, f in enumerate(freqs) if f > median)
    return bits - (1 << _BITS) if bits >= 1 << (_BITS - 1) else bits


def distance(a: int, b: int) -> float:
    """How far apart two perceptual hashes are: the share of their bits that
    differ, from 0 (the same) to 1."""
    return ((a ^ b) & ((1 << _BITS) - 1)).bit_count() / _BITS
