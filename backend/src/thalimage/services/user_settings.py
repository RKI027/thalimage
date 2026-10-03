"""User preferences, stored as key/value text in the settings table."""

import sqlite3

from pydantic import BaseModel


class UserSettings(BaseModel):
    show_nsfw: bool = False


def read(conn: sqlite3.Connection) -> UserSettings:
    """The stored preferences; anything never set keeps its model default."""
    stored = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}
    settings = UserSettings()
    if "show_nsfw" in stored:
        settings.show_nsfw = stored["show_nsfw"] == "true"
    return settings


def write(conn: sqlite3.Connection, *, show_nsfw: bool | None = None) -> UserSettings:
    """Store the given preferences (None leaves one unchanged) and commit."""
    if show_nsfw is not None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('show_nsfw', ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("true" if show_nsfw else "false",),
        )
        conn.commit()
    return read(conn)
