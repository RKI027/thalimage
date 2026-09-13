"""Build version endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from thalimage.version import version_info

router = APIRouter(prefix="/version", tags=["version"])


class Version(BaseModel):
    version: str
    commit: str | None


@router.get("", response_model=Version)
def get_version() -> Version:
    info = version_info()
    return Version(version=info.version, commit=info.commit)
