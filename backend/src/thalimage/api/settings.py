"""User settings endpoints."""

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from thalimage.deps import get_db
from thalimage.services import user_settings
from thalimage.services.user_settings import UserSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class UserSettingsPatch(BaseModel):
    show_nsfw: bool | None = None


@router.get("", response_model=UserSettings)
def read_user_settings(db: sqlite3.Connection = Depends(get_db)) -> UserSettings:
    return user_settings.read(db)


@router.patch("", response_model=UserSettings)
def patch_user_settings(
    body: UserSettingsPatch,
    db: sqlite3.Connection = Depends(get_db),
) -> UserSettings:
    return user_settings.write(db, show_nsfw=body.show_nsfw)
