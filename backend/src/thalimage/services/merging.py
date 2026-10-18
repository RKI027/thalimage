"""Merging images into another: one picture is kept, and the others' history
is carried over to it."""

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from thalimage.services.file_deletion import DeletionResult, delete_images, is_live
from thalimage.services.picture_edits import merge_keys


@dataclass
class MergeResult:
    deletion: DeletionResult
    merged: list[str] = field(default_factory=list)


def merge_images(conn: sqlite3.Connection, kept: str, hashes: list[str]) -> Optional[MergeResult]:
    """Merge each image of `hashes` into `kept`: every copy is deleted from
    disk, then its tags, collections, votes, scores and file versions go to
    `kept` (`merge_keys`), votes between the two dropped. None if `kept` is
    not a live image; `kept` itself and unknown images are skipped.

    Refused as a whole, before anything changes, unless every copy may be
    deleted (see `delete_images`). An image a file of which then fails to
    be removed is not merged: it keeps its history and remaining copies.
    """
    if not is_live(conn, kept):
        return None
    merging = [h for h in dict.fromkeys(hashes) if h != kept and is_live(conn, h)]
    result = MergeResult(delete_images(conn, merging))
    with conn:
        for content_hash in merging:
            if not is_live(conn, content_hash):
                merge_keys(conn, content_hash, kept)
                result.merged.append(content_hash)
    return result
