"""Image scanning and discovery."""

import os
from pathlib import Path

IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".mp4",
}


def scan_directory(root: Path, *, recursive: bool = True) -> list[Path]:
    """Find all supported image/video files under root.

    Returns paths sorted alphabetically.
    """
    if not root.exists():
        return []

    paths: list[Path] = []
    try:
        if recursive:
            for dir_path_str, _, file_names in os.walk(root):
                dir_path = Path(dir_path_str)
                for name in file_names:
                    fp = dir_path / name
                    if fp.suffix.lower() in IMAGE_EXTENSIONS:
                        paths.append(fp)
        else:
            for entry in os.scandir(root):
                if entry.is_file() and Path(entry.name).suffix.lower() in IMAGE_EXTENSIONS:
                    paths.append(Path(entry.path))
    except (OSError, PermissionError):
        pass

    paths.sort()
    return paths
