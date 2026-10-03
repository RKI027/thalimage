"""Image browsing and serving endpoints."""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from thalimage.core.previews import PREVIEW_SIZES, generate_preview, nearest_size
from thalimage.core.thumbnails import thumbnail_path
from thalimage.deps import ContentHash, get_db, get_preview_dir, get_thumb_dir
from thalimage.services.collection_service import resolve_scope
from thalimage.services.image_service import (
    ImageDetail,
    ImagePage,
    InvalidCursor,
    get_image,
    list_images,
    resolve_file_path,
    set_archived,
)

router = APIRouter(prefix="/images", tags=["images"])

# Responses are addressed by content hash, so a given URL can never change
# meaning. Caching them for a year removes a revalidation round-trip per
# tile, which dominates gallery load time on a slow link.
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}

# Hi-DPI screens ask for more than the largest bucket (a 1512px-wide window
# at dpr 2 asks for 3024); those requests get the largest bucket. Only
# values no screen could need are rejected.
MAX_PREVIEW_REQUEST = 16384


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

    # A collection becomes the filter that selects its images.
    if collection_id is not None:
        scope = resolve_scope(db, collection_id)
        if scope is not None:
            source_id = scope.source_id or source_id
            collection_id = scope.collection_id

    try:
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
    except InvalidCursor as exc:
        raise HTTPException(400, str(exc)) from exc


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
    return FileResponse(p, headers=IMMUTABLE)


@router.get("/{content_hash}/thumb")
def get_image_thumb(
    content_hash: ContentHash,
    thumb_dir: Path = Depends(get_thumb_dir),
) -> FileResponse:
    p = thumbnail_path(thumb_dir, content_hash)
    if not p.exists():
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(p, media_type="image/webp", headers=IMMUTABLE)


@router.get("/{content_hash}/preview")
def get_image_preview(
    content_hash: ContentHash,
    size: int = Query(
        PREVIEW_SIZES[0],
        ge=1,
        # A sanity bound, not the largest bucket: anything up to it is
        # served, and sizes above the largest bucket get that bucket.
        le=MAX_PREVIEW_REQUEST,
        description=(
            "Desired long edge in pixels; snapped up to the nearest bucket,"
            f" or down to {PREVIEW_SIZES[-1]} when larger than every bucket."
        ),
    ),
    db: sqlite3.Connection = Depends(get_db),
    preview_dir: Path = Depends(get_preview_dir),
) -> FileResponse:
    """Serve a display-sized WebP, generating and caching it on first request."""
    file_path = resolve_file_path(db, content_hash)
    if file_path is None:
        raise HTTPException(404, "Image not found")
    source = Path(file_path)
    if not source.exists():
        raise HTTPException(404, "File not found on disk")

    bucket = nearest_size(size)
    try:
        p = generate_preview(source, preview_dir, content_hash, bucket)
    except ValueError as exc:
        raise HTTPException(415, "No preview available for this file type") from exc

    return FileResponse(
        p,
        media_type="image/webp",
        headers={**IMMUTABLE, "X-Preview-Size": str(bucket)},
    )


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
