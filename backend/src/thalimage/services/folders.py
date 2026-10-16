"""Folder tags: the `folder:<dir>` tags an image has from where its files
are, derived from image_locations and never stored."""

import sqlite3
from pathlib import PurePosixPath
from typing import Optional

FOLDER_TAG_PREFIX = "folder:"


def is_folder_tag(tag_name: str) -> bool:
    """Whether `tag_name` is in the folder tags' namespace, whatever its case."""
    return tag_name[: len(FOLDER_TAG_PREFIX)].lower() == FOLDER_TAG_PREFIX


def tagged_folder(tag_name: str) -> Optional[str]:
    """The folder a `folder:` tag names, without surrounding slashes;
    None for any other tag."""
    if not is_folder_tag(tag_name):
        return None
    return tag_name[len(FOLDER_TAG_PREFIX):].strip("/")


def in_folder_sql(hash_col: str = "content_hash") -> str:
    """SQL condition: the image has a location in the given folder or below.
    Takes the folder followed by "/" as two parameters (see
    `in_folder_params`)."""
    return (
        f"{hash_col} IN (SELECT content_hash FROM image_locations"
        " WHERE substr(relative_path, 1, length(?)) = ?)"
    )


def in_folder_params(folder: str) -> tuple[str, str]:
    """The parameters `in_folder_sql` takes for `folder`."""
    prefix = f"{folder}/"
    return prefix, prefix


def folder_tags(conn: sqlite3.Connection, content_hash: str) -> list[str]:
    """The image's folder tags, one per folder holding a copy, sorted. A
    file directly in its source folder gives none."""
    rows = conn.execute(
        "SELECT relative_path FROM image_locations WHERE content_hash = ?", (content_hash,)
    ).fetchall()
    folders = {str(PurePosixPath(r["relative_path"]).parent) for r in rows} - {"."}
    return [f"{FOLDER_TAG_PREFIX}{f}" for f in sorted(folders)]
