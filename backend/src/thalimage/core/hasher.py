"""SHA-256 content hashing for images."""

import hashlib
from pathlib import Path

CHUNK_SIZE = 65536  # 64 KB


def content_hash(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()
