"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from fastapi import Path as PathParam
from fastapi import Request

from thalimage.db.engine import connect

if TYPE_CHECKING:
    from thalimage.services.scan_manager import ScanManager

# Content hashes are SHA-256 hex digests. Constraining the path param keeps
# attacker-controlled values out of filesystem paths and DB lookups.
ContentHash = Annotated[str, PathParam(pattern=r"^[0-9a-f]{64}$")]

# Documentation slugs address files on disk; constrain them at the edge.
DocSlug = Annotated[str, PathParam(pattern=r"^[a-z0-9-]+$")]

DOCS_DIR = Path(__file__).resolve().parent / "docs"


def open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a connection of its own to one request, then close it.

    Whatever the request leaves uncommitted, such as a write that failed
    halfway, is rolled back here. Otherwise the open transaction would keep
    the write lock (and the scan worker would fail with "database is
    locked") until some unrelated commit persisted the partial work.
    Sync dependencies may be torn down on a different threadpool thread
    than the one that opened them, hence check_same_thread=False.
    """
    conn = connect(db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """A per-request DB connection (see open_db)."""
    yield from open_db(request.app.state.db_path)


def get_thumb_dir(request: Request) -> Path:
    """Get the thumbnail directory."""
    thumb_dir: Path = request.app.state.settings.resolved_thumb_dir
    return thumb_dir


def get_preview_dir(request: Request) -> Path:
    """Get the preview directory."""
    preview_dir: Path = request.app.state.settings.resolved_preview_dir
    return preview_dir


def get_docs_dir() -> Path:
    """Get the directory holding the documentation Markdown files."""
    return DOCS_DIR


def get_scan_manager(request: Request) -> ScanManager:
    """Get the scan manager from app state."""
    mgr: ScanManager = request.app.state.scan_manager
    return mgr
