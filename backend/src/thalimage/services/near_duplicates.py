"""Near-duplicates: images whose pictures look alike, in groups.

Every pair of live images within WIDEST_THRESHOLD of each other is kept
in memory. The first search compares all pairs; later ones compare only
the images added or changed since, and drop those gone, so a deletion or
a scan does not stall the listing. A search at any threshold up to the
widest only filters those pairs, so moving the threshold regroups at once.
Kept on disk too (`keep_on_disk`), a restart only compares what changed
while it was down.
"""

import json
import logging
import os
import sqlite3
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from thalimage.core.perceptual_hash import BITS

logger = logging.getLogger(__name__)

# The widest threshold a search takes, as a perceptual distance.
WIDEST_THRESHOLD = 0.30
_WIDEST_BITS = round(WIDEST_THRESHOLD * BITS)

# Raised when the file's layout changes, so an older file is not read.
_FILE_FORMAT = 1

# Each image's near pictures, as (key, differing bits).
_Near = dict[str, list[tuple[str, int]]]
# The perceptual hashes by key that the near pictures were found among.
_Pictures = dict[str, int]
_found: tuple[_Pictures, _Near] = ({}, {})
_kept_at: Optional[Path] = None
_lock = threading.Lock()


def keep_on_disk(path: Path) -> None:
    """Keep the pairs found in the file at `path`, starting from those it
    holds. A file missing, unreadable or written for another hash length
    or widest threshold is ignored: the next search compares all pairs."""
    global _found, _kept_at
    with _lock:
        _kept_at = path
        _found = _read(path)


def groups(conn: sqlite3.Connection, ordered: Sequence[str], threshold: float) -> list[list[str]]:
    """The near-duplicate groups among the images `ordered`, in that order.
    The first image not yet grouped starts a group, joined by every image
    not yet grouped within `threshold` of it; a group holds two images at
    least, and an image lies in one group at most."""
    near = _near_pictures(conn)
    rank = {key: i for i, key in enumerate(ordered)}
    within = round(threshold * BITS)
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
            if _kept_at is not None:
                _write(_kept_at, *_found)
        return _found[1]


def _read(path: Path) -> tuple[_Pictures, _Near]:
    try:
        kept = json.loads(path.read_text())
        if (kept["format"], kept["bits"], kept["widest_bits"]) != (_FILE_FORMAT, BITS, _WIDEST_BITS):
            return {}, {}
        keys = kept["keys"]
        pictures = dict(zip(keys, kept["pictures"], strict=True))
        near: _Near = {}
        for i, j, bits in kept["pairs"]:
            near.setdefault(keys[i], []).append((keys[j], bits))
            near.setdefault(keys[j], []).append((keys[i], bits))
        return pictures, near
    except FileNotFoundError:
        return {}, {}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        logger.warning("Ignoring the near-duplicate pairs kept in %s: %s", path, exc)
        return {}, {}


def _write(path: Path, pictures: _Pictures, near: _Near) -> None:
    """Write the pairs to `path` whole or not at all: through a file beside
    it, renamed over it. Each pair is written once."""
    keys = list(pictures)
    index = {k: i for i, k in enumerate(keys)}
    kept = {
        "format": _FILE_FORMAT,
        "bits": BITS,
        "widest_bits": _WIDEST_BITS,
        "keys": keys,
        "pictures": [pictures[k] for k in keys],
        "pairs": [
            [index[k], index[o], bits]
            for k, found in near.items()
            for o, bits in found
            if index[k] < index[o]
        ],
    }
    partial = path.with_name(path.name + ".partial")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial.write_text(json.dumps(kept, separators=(",", ":")))
        os.replace(partial, path)
    except OSError as exc:
        logger.warning("Could not keep the near-duplicate pairs in %s: %s", path, exc)


def _updated(before: _Pictures, near: _Near, pictures: _Pictures) -> _Near:
    """The near pictures among `pictures`, from those found among `before`.
    A new mapping: a search may still be reading the old one."""
    changed = [k for k, p in pictures.items() if before.get(k) != p]
    changed_keys = set(changed)
    gone = {k for k, p in before.items() if pictures.get(k) != p}
    updated: _Near = {
        k: [(o, bits) for o, bits in v if o not in gone] for k, v in near.items() if k not in gone
    }
    # The changed images first: each meets every image after it, so the
    # changed meet one another and the settled once, and settled pairs,
    # already known, are not compared again.
    keys = changed + [k for k in pictures if k not in changed_keys]
    values = [pictures[k] for k in keys]
    for i in range(len(changed)):
        key, picture = keys[i], values[i]
        for j, other in enumerate(values[i + 1 :], i + 1):
            bits = (picture ^ other).bit_count()
            if bits <= _WIDEST_BITS:
                updated.setdefault(key, []).append((keys[j], bits))
                updated.setdefault(keys[j], []).append((key, bits))
    return updated
