"""Image scanning and discovery."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from thalimage.core.video import VIDEO_EXTENSIONS

IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
}

SUPPORTED_EXTENSIONS: set[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class SourceUnavailable(OSError):
    """The source folder is missing, not a directory, or cannot be listed."""


@dataclass
class Listing:
    files: list[Path] = field(default_factory=list)
    # Directories below the root that could not be listed. Their contents
    # are unknown, not absent, so nothing under them may be marked deleted.
    unreadable: list[Path] = field(default_factory=list)


def scan_directory(root: Path, *, recursive: bool = True) -> Listing:
    """Find all supported image/video files under root, sorted.

    Raises SourceUnavailable when root itself cannot be read: an unmounted
    or unreadable folder must fail the scan, not look like an empty one.
    """
    if not root.is_dir():
        raise SourceUnavailable(f"Source folder is missing or not a directory: {root}")

    listing = Listing()
    if recursive:
        errors: list[OSError] = []
        for dir_path_str, _, file_names in os.walk(root, onerror=errors.append):
            dir_path = Path(dir_path_str)
            for name in file_names:
                fp = dir_path / name
                if fp.suffix.lower() in SUPPORTED_EXTENSIONS:
                    listing.files.append(fp)
        for err in errors:
            failed = Path(err.filename) if err.filename else root
            if failed == root:
                raise SourceUnavailable(f"Cannot read source folder {root}: {err}") from err
            listing.unreadable.append(failed)
    else:
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    if entry.is_file() and Path(entry.name).suffix.lower() in SUPPORTED_EXTENSIONS:
                        listing.files.append(Path(entry.path))
        except OSError as err:
            raise SourceUnavailable(f"Cannot read source folder {root}: {err}") from err

    listing.files.sort()
    listing.unreadable.sort()
    return listing
