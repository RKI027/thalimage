"""User preferences, stored as key/value text in the settings table."""

import sqlite3

from pydantic import BaseModel


class UserSettings(BaseModel):
    show_nsfw: bool = False
    # The perceptual distance at or under which a picture changed in place
    # is offered as an edit of the one it replaced.
    edit_threshold: float = 0.25
    # The perceptual distance at or under which two images are grouped as
    # near-duplicates.
    near_duplicate_threshold: float = 0.15


def read(conn: sqlite3.Connection) -> UserSettings:
    """The stored preferences; anything never set keeps its model default."""
    stored = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}
    settings = UserSettings()
    if "show_nsfw" in stored:
        settings.show_nsfw = stored["show_nsfw"] == "true"
    if "edit_threshold" in stored:
        settings.edit_threshold = float(stored["edit_threshold"])
    if "near_duplicate_threshold" in stored:
        settings.near_duplicate_threshold = float(stored["near_duplicate_threshold"])
    return settings


def write(
    conn: sqlite3.Connection,
    *,
    show_nsfw: bool | None = None,
    edit_threshold: float | None = None,
    near_duplicate_threshold: float | None = None,
) -> UserSettings:
    """Store the given preferences (None leaves one unchanged) and commit."""
    values = {
        "show_nsfw": None if show_nsfw is None else ("true" if show_nsfw else "false"),
        "edit_threshold": None if edit_threshold is None else str(edit_threshold),
        "near_duplicate_threshold": (
            None if near_duplicate_threshold is None else str(near_duplicate_threshold)
        ),
    }
    with conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(k, v) for k, v in values.items() if v is not None],
        )
    return read(conn)
