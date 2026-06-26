"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from thalimage.services.scan_manager import ScanManager


def get_db(request: Request) -> sqlite3.Connection:
    """Get the shared DB connection from app state."""
    conn: sqlite3.Connection = request.app.state.db
    return conn


def get_thumb_dir(request: Request) -> Path:
    """Get the thumbnail directory."""
    thumb_dir: Path = request.app.state.settings.resolved_thumb_dir
    return thumb_dir


def get_scan_manager(request: Request) -> ScanManager:
    """Get the scan manager from app state."""
    mgr: ScanManager = request.app.state.scan_manager
    return mgr
