"""Near-duplicates: images whose pictures look alike, in groups.

Every pair of live images within WIDEST_THRESHOLD of each other is found
in one pass over all pairs, and kept in memory until a perceptual hash
or key changes. A search at any threshold up to it only filters those
pairs, so moving the threshold regroups at once.
"""

import sqlite3
import threading
from collections.abc import Sequence

from thalimage.core.perceptual_hash import BITS

# The widest threshold a search takes, as a perceptual distance.
WIDEST_THRESHOLD = 0.30

# Each image's near pictures, as (key, differing bits), for the rows
# (key, perceptual hash) they were found among.
_Near = dict[str, list[tuple[str, int]]]
_found: tuple[list[tuple[str, int]], _Near] | None = None
_lock = threading.Lock()


def groups(conn: sqlite3.Connection, ordered: Sequence[str], threshold: float) -> list[list[str]]:
    """The near-duplicate groups among the images `ordered`, in that order.
    The first image not yet grouped starts a group, joined by every image
    not yet grouped within `threshold` of it; a group holds two images at
    least, and an image lies in one group at most."""
    near = _near_pictures(conn)
    rank = {key: i for i, key in enumerate(ordered)}
    within = int(threshold * BITS)
    grouped: set[str] = set()
    found = []
    for key in ordered:
        if key in grouped:
            continue
        members = sorted(
            (k for k, bits in near.get(key, ()) if bits <= within and k in rank and k not in grouped),
            key=rank.__getitem__,
        )
        if members:
            group = [key, *members]
            grouped.update(group)
            found.append(group)
    return found


def _near_pictures(conn: sqlite3.Connection) -> _Near:
    global _found
    mask = (1 << BITS) - 1
    rows = [
        (r[0], r[1] & mask)
        for r in conn.execute(
            "SELECT content_hash, perceptual_hash FROM images"
            " WHERE deleted = 0 AND perceptual_hash IS NOT NULL ORDER BY content_hash"
        )
    ]
    with _lock:
        if _found is None or _found[0] != rows:
            _found = (rows, _all_pairs(rows))
        return _found[1]


def _all_pairs(rows: list[tuple[str, int]]) -> _Near:
    widest = int(WIDEST_THRESHOLD * BITS)
    pictures = [p for _, p in rows]
    near: _Near = {}
    for i, (key, picture) in enumerate(rows):
        for j, other in enumerate(pictures[i + 1 :], i + 1):
            bits = (picture ^ other).bit_count()
            if bits <= widest:
                near.setdefault(key, []).append((rows[j][0], bits))
                near.setdefault(rows[j][0], []).append((key, bits))
    return near
