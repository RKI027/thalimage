"""Image browsing and serving endpoints."""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from thalimage.deps import get_db, get_thumb_dir
from thalimage.core.thumbnails import thumbnail_path
from thalimage.services.image_service import (
    ImageDetail,
    ImagePage,
    get_image,
    list_images,
    resolve_file_path,
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
    db: sqlite3.Connection = Depends(get_db),
) -> ImagePage:
    return list_images(
        db,
        cursor=cursor,
        limit=limit,
        sort=sort,
        direction=dir,
        source_id=source_id,
        collection_id=collection_id,
    )


@router.get("/{content_hash}", response_model=ImageDetail)
def get_image_detail(
    content_hash: str,
    db: sqlite3.Connection = Depends(get_db),
) -> ImageDetail:
    image = get_image(db, content_hash)
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


@router.get("/{content_hash}/file")
def get_image_file(
    content_hash: str,
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
    content_hash: str,
    thumb_dir: Path = Depends(get_thumb_dir),
) -> FileResponse:
    p = thumbnail_path(thumb_dir, content_hash)
    if not p.exists():
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(p, media_type="image/webp")
