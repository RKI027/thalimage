"""Shared FastAPI dependencies."""

import sqlite3
from pathlib import Path

from fastapi import Request


def get_db(request: Request) -> sqlite3.Connection:
    """Get the shared DB connection from app state."""
    conn: sqlite3.Connection = request.app.state.db
    return conn


def get_thumb_dir(request: Request) -> Path:
    """Get the thumbnail directory."""
    thumb_dir: Path = request.app.state.settings.resolved_thumb_dir
    return thumb_dir
