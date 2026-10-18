"""Near-duplicates: images whose pictures look alike, in groups.

Every pair of live images within WIDEST_THRESHOLD of each other is kept
in memory. The first search compares all pairs; later ones compare only
the images added or changed since, and drop those gone, so a deletion or
a scan does not stall the listing. A search at any threshold up to the
widest only filters those pairs, so moving the threshold regroups at once.
"""

import sqlite3
import threading
from collections.abc import Sequence
from typing import Optional

from thalimage.core.perceptual_hash import BITS

# The widest threshold a search takes, as a perceptual distance.
WIDEST_THRESHOLD = 0.30

# Each image's near pictures, as (key, differing bits).
_Near = dict[str, list[tuple[str, int]]]
# The perceptual hashes by key that the near pictures were found among.
_Pictures = dict[str, int]
_found: tuple[_Pictures, _Near] = ({}, {})
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


def places(
    conn: sqlite3.Connection, ordered: Sequence[str], threshold: float
) -> list[tuple[str, Optional[int]]]:
    """Every image of `ordered` with its group (see `groups`), or None,
    in the order a grouped listing walks them: each group where its first
    image sorts, and each image in no group in its own place, so it keeps
    neighbours among the groups."""
    found = groups(conn, ordered, threshold)
    starting = {images[0]: g for g, images in enumerate(found)}
    grouped = {image for images in found for image in images}
    walked: list[tuple[str, Optional[int]]] = []
    for image in ordered:
        if image in starting:
            g = starting[image]
            walked += [(member, g) for member in found[g]]
        elif image not in grouped:
            walked.append((image, None))
    return walked


def _near_pictures(conn: sqlite3.Connection) -> _Near:
    global _found
    mask = (1 << BITS) - 1
    pictures = {
        r[0]: r[1] & mask
        for r in conn.execute(
            "SELECT content_hash, perceptual_hash FROM images"
            " WHERE deleted = 0 AND perceptual_hash IS NOT NULL"
        )
    }
    with _lock:
        if _found[0] != pictures:
            _found = (pictures, _updated(*_found, pictures))
        return _found[1]


def _updated(before: _Pictures, near: _Near, pictures: _Pictures) -> _Near:
    """The near pictures among `pictures`, from those found among `before`.
    A new mapping: a search may still be reading the old one."""
    changed = [k for k, p in pictures.items() if before.get(k) != p]
    changed_keys = set(changed)
    gone = {k for k, p in before.items() if pictures.get(k) != p}
    updated: _Near = {
        k: [(o, bits) for o, bits in v if o not in gone] for k, v in near.items() if k not in gone
    }
    widest = int(WIDEST_THRESHOLD * BITS)
    # The changed images first: each meets every image after it, so the
    # changed meet one another and the settled once, and settled pairs,
    # already known, are not compared again.
    keys = changed + [k for k in pictures if k not in changed_keys]
    values = [pictures[k] for k in keys]
    for i in range(len(changed)):
        key, picture = keys[i], values[i]
        for j, other in enumerate(values[i + 1 :], i + 1):
            bits = (picture ^ other).bit_count()
            if bits <= widest:
                updated.setdefault(key, []).append((keys[j], bits))
                updated.setdefault(keys[j], []).append((key, bits))
    return updated
