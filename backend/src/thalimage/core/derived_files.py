"""The files the app derives from an image and names after its key: the
thumbnail, the previews and the playable video copy."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from thalimage.core.previews import preview_path
from thalimage.core.thumbnails import thumbnail_path
from thalimage.core.video import playable_copy_path


@dataclass(frozen=True)
class DerivedDirs:
    thumbs: Path
    previews: Optional[Path] = None
    videos: Optional[Path] = None


def derived_paths(dirs: DerivedDirs, key: str) -> list[Path]:
    """Where the files derived from the image keyed `key` would be, in a
    fixed order, whether they exist or not."""
    paths = [thumbnail_path(dirs.thumbs, key)]
    if dirs.previews is not None and dirs.previews.is_dir():
        sizes = sorted(int(d.name) for d in dirs.previews.iterdir() if d.name.isdigit())
        paths += [preview_path(dirs.previews, key, size) for size in sizes]
    if dirs.videos is not None:
        paths.append(playable_copy_path(dirs.videos, key))
    return paths


def link_derived(dirs: DerivedDirs, old: str, new: str) -> None:
    """Give the image keyed `new` the derived files of the one keyed `old`,
    where it has none yet. They are hard-linked, so both keys hold them
    until `remove_derived` drops the old one, and copied where a link
    cannot be made."""
    for source, target in zip(derived_paths(dirs, old), derived_paths(dirs, new), strict=True):
        if not source.exists() or target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)


def remove_derived(dirs: DerivedDirs, key: str) -> None:
    """Delete the files derived from the image keyed `key`."""
    for path in derived_paths(dirs, key):
        path.unlink(missing_ok=True)
