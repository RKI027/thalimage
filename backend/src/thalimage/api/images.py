"""Image browsing and serving endpoints."""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from thalimage.core.thumbnails import thumbnail_path
from thalimage.deps import ContentHash, get_db, get_thumb_dir
from thalimage.services.collection_service import get_collection
from thalimage.services.image_service import (
    ImageDetail,
    ImagePage,
    get_image,
    list_images,
    resolve_file_path,
    set_archived,
)

router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=ImagePage)
def get_images(
    cursor: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    sort: str = Query("name"),
    dir: str = Query("asc"),
    source_id: Optional[int] = Query(None),
    collection_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    aspect_ratio_filter: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    tags: Optional[list[str]] = Query(None),
    show_nsfw: bool = Query(False),
    db: sqlite3.Connection = Depends(get_db),
) -> ImagePage:
    # ELO scores are keyed by the collection being viewed; capture it before the
    # source-preset rewrite below nulls collection_id.
    elo_collection_id = collection_id if sort == "elo" else None

    # Source preset collections are served dynamically: rewrite to a source filter.
    if collection_id is not None:
        coll = get_collection(db, collection_id)
        if coll is not None and coll.type == "source_preset":
            source_id = coll.source_id
            collection_id = None

    return list_images(
        db,
        cursor=cursor,
        limit=limit,
        sort=sort,
        direction=dir,
        source_id=source_id,
        collection_id=collection_id,
        date_from=date_from,
        date_to=date_to,
        aspect_ratio_filter=aspect_ratio_filter,
        media_type=media_type,
        tags=tags,
        show_nsfw=show_nsfw,
        elo_collection_id=elo_collection_id,
    )


@router.get("/{content_hash}", response_model=ImageDetail)
def get_image_detail(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> ImageDetail:
    image = get_image(db, content_hash)
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


@router.get("/{content_hash}/file")
def get_image_file(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> FileResponse:
    file_path = resolve_file_path(db, content_hash)
    if file_path is None:
        raise HTTPException(404, "Image not found")
    p = Path(file_path)
    if not p.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(p)


@router.get("/{content_hash}/thumb")
def get_image_thumb(
    content_hash: ContentHash,
    thumb_dir: Path = Depends(get_thumb_dir),
) -> FileResponse:
    p = thumbnail_path(thumb_dir, content_hash)
    if not p.exists():
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(p, media_type="image/webp")


class ArchiveRequest(BaseModel):
    archived: bool


@router.patch("/{content_hash}/archive", response_model=ImageDetail)
def archive_image(
    content_hash: ContentHash,
    body: ArchiveRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> ImageDetail:
    if not set_archived(db, content_hash, body.archived):
        raise HTTPException(404, "Image not found")
    image = get_image(db, content_hash)
    assert image is not None
    return image
