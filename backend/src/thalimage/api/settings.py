"""User settings endpoints."""

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from thalimage.deps import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

_DEFAULTS: dict[str, object] = {
    "show_nsfw": False,
}


def _read_settings(conn: sqlite3.Connection) -> dict[str, object]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    result: dict[str, object] = dict(_DEFAULTS)
    for row in rows:
        key, value = row["key"], row["value"]
        if key == "show_nsfw":
            result[key] = value == "true"
        else:
            result[key] = value
    return result


class UserSettings(BaseModel):
    show_nsfw: bool = False


class UserSettingsPatch(BaseModel):
    show_nsfw: bool | None = None


@router.get("", response_model=UserSettings)
def get_settings(
    db: sqlite3.Connection = Depends(get_db),
) -> UserSettings:
    data = _read_settings(db)
    return UserSettings(show_nsfw=bool(data.get("show_nsfw", False)))


@router.patch("", response_model=UserSettings)
def patch_settings(
    body: UserSettingsPatch,
    db: sqlite3.Connection = Depends(get_db),
) -> UserSettings:
    if body.show_nsfw is not None:
        db.execute(
            "INSERT INTO settings (key, value) VALUES ('show_nsfw', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("true" if body.show_nsfw else "false",),
        )
        db.commit()
    return get_settings(db)
