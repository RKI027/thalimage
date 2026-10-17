"""Image scanning and discovery."""

import os
from fnmatch import fnmatchcase
from dataclasses import dataclass, field
from pathlib import Path

from thalimage.core.video import VIDEO_EXTENSIONS

IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".avif",
}

SUPPORTED_EXTENSIONS: set[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


# What operating systems and NAS software leave in folders: never indexed,
# never sidecars. Matched case-insensitively against the name.
IGNORED_FILES = (".ds_store", "._*", "thumbs.db", "desktop.ini", "*@synoeastream")
IGNORED_FOLDERS = ("@eadir", "#recycle", ".trash*", "$recycle.bin")


def _ignored(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(name.lower(), p) for p in patterns)


def is_media(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


class SourceUnavailable(OSError):
    """The source folder is missing, not a directory, or cannot be listed."""


@dataclass
class Listing:
    files: list[Path] = field(default_factory=list)
    # Every other file: sidecars, and files no media file names.
    others: list[Path] = field(default_factory=list)
    # Directories below the root that could not be listed. Their contents
    # are unknown, not absent, so nothing under them may be marked deleted.
    unreadable: list[Path] = field(default_factory=list)


def scan_directory(root: Path, *, recursive: bool = True) -> Listing:
    """Find all supported image/video files under root, sorted, and the
    other files beside them, leaving out system files and folders.

    Raises SourceUnavailable when root itself cannot be read: an unmounted
    or unreadable folder must fail the scan, not look like an empty one.
    """
    if not root.is_dir():
        raise SourceUnavailable(f"Source folder is missing or not a directory: {root}")

    listing = Listing()
    if recursive:
        errors: list[OSError] = []
        for dir_path_str, dir_names, file_names in os.walk(root, onerror=errors.append):
            dir_path = Path(dir_path_str)
            dir_names[:] = [d for d in dir_names if not _ignored(d, IGNORED_FOLDERS)]
            for name in file_names:
                if _ignored(name, IGNORED_FILES):
                    continue
                fp = dir_path / name
                (listing.files if is_media(fp) else listing.others).append(fp)
        for err in errors:
            failed = Path(err.filename) if err.filename else root
            if failed == root:
                raise SourceUnavailable(f"Cannot read source folder {root}: {err}") from err
            listing.unreadable.append(failed)
    else:
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    if entry.is_file() and not _ignored(entry.name, IGNORED_FILES):
                        fp = Path(entry.path)
                        (listing.files if is_media(fp) else listing.others).append(fp)
        except OSError as err:
            raise SourceUnavailable(f"Cannot read source folder {root}: {err}") from err

    listing.files.sort()
    listing.others.sort()
    listing.unreadable.sort()
    return listing
