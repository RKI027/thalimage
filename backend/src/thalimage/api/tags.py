"""Tag management endpoints."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from thalimage.deps import get_db
from thalimage.services.tag_service import (
    Tag,
    add_image_tag,
    create_tag,
    delete_tag,
    get_image_tags,
    get_tag,
    list_tags,
    remove_image_tag,
    update_tag,
)

router = APIRouter(tags=["tags"])


class TagCreate(BaseModel):
    name: str
    nsfw: bool = False


class TagUpdate(BaseModel):
    name: Optional[str] = None
    nsfw: Optional[bool] = None


class ImageTagBody(BaseModel):
    tag_id: int


@router.get("/tags", response_model=list[Tag])
def get_tags(
    search: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
) -> list[Tag]:
    return list_tags(db, search=search)


@router.post("/tags", response_model=Tag, status_code=201)
def post_tag(
    body: TagCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> Tag:
    try:
        return create_tag(db, body.name, nsfw=body.nsfw)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, f"Tag '{body.name}' already exists") from exc


@router.patch("/tags/{tag_id}", response_model=Tag)
def patch_tag(
    tag_id: int,
    body: TagUpdate,
    db: sqlite3.Connection = Depends(get_db),
) -> Tag:
    result = update_tag(db, tag_id, name=body.name, nsfw=body.nsfw)
    if result is None:
        raise HTTPException(404, "Tag not found")
    return result


@router.delete("/tags/{tag_id}", status_code=204)
def del_tag(
    tag_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    if not delete_tag(db, tag_id):
        raise HTTPException(404, "Tag not found")


@router.get("/images/{content_hash}/tags", response_model=list[Tag])
def get_tags_for_image(
    content_hash: str,
    db: sqlite3.Connection = Depends(get_db),
) -> list[Tag]:
    return get_image_tags(db, content_hash)


@router.post("/images/{content_hash}/tags", status_code=204)
def post_image_tag(
    content_hash: str,
    body: ImageTagBody,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    if get_tag(db, body.tag_id) is None:
        raise HTTPException(404, "Tag not found")
    add_image_tag(db, content_hash, body.tag_id)


@router.delete("/images/{content_hash}/tags/{tag_id}", status_code=204)
def del_image_tag(
    content_hash: str,
    tag_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    if not remove_image_tag(db, content_hash, tag_id):
        raise HTTPException(404, "Tag not found on image")
