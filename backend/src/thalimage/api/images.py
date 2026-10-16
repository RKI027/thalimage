"""Image browsing and serving endpoints."""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from thalimage.core.sidecars import text_of
from thalimage.core.previews import PREVIEW_SIZES, generate_preview, nearest_size
from thalimage.core.thumbnails import thumbnail_path
from thalimage.core.video import playable_copy_path
from thalimage.deps import ContentHash, get_db, get_preview_dir, get_thumb_dir, get_video_dir
from thalimage.services.collection_service import resolve_scope
from thalimage.services.elo_ranking import elo_cut
from thalimage.services.elo_service import EloStanding, image_standings
from thalimage.services.file_changes import SourceNotWritable
from thalimage.services.file_deletion import Copy, DeletionRefused, delete_image, image_copies
from thalimage.services.image_service import (
    ImageDetail,
    ImagePage,
    InvalidCursor,
    ListingFilters,
    Neighbors,
    SequenceItem,
    get_image,
    listing_page,
    neighbors,
    resolve_file_path,
    sequence,
    set_archived,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Responses are addressed by content hash, so a given URL can never change
# meaning. Caching them for a year removes a revalidation round-trip per
# tile, which dominates gallery load time on a slow link.
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}

# Hi-DPI screens ask for more than the largest bucket (a 1512px-wide window
# at dpr 2 asks for 3024); those requests get the largest bucket. Only
# values no screen could need are rejected.
MAX_PREVIEW_REQUEST = 16384


@dataclass(frozen=True)
class Listing:
    """A listing as a request names it: its sort, direction and filters."""

    sort: str
    direction: str
    filters: ListingFilters
    # The collection being viewed. ELO scores and rankings are keyed by it,
    # and a source preset's is not in `filters`, which select by source.
    browsed_collection_id: Optional[int]

    @property
    def elo_collection_id(self) -> Optional[int]:
        """The collection to order by ELO in, when sorted by ELO."""
        return self.browsed_collection_id if self.sort == "elo" else None


def listing(
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
    elo_end: Literal["top", "bottom"] = Query("top"),
    elo_percent: Optional[int] = Query(None, ge=1, le=100),
    db: sqlite3.Connection = Depends(get_db),
) -> Listing:
    """The query parameters every listing route reads, as a Listing."""
    # Capture the collection viewed before the source-preset rewrite below
    # nulls collection_id.
    browsed_collection_id = collection_id
    cut = elo_cut(collection_id, elo_end, elo_percent)

    # A collection becomes the filter that selects its images.
    if collection_id is not None:
        scope = resolve_scope(db, collection_id)
        if scope is not None:
            source_id = scope.source_id or source_id
            collection_id = scope.collection_id

    return Listing(
        sort=sort,
        direction=dir,
        filters=ListingFilters(
            source_id=source_id,
            collection_id=collection_id,
            date_from=date_from,
            date_to=date_to,
            aspect_ratio_filter=aspect_ratio_filter,
            media_type=media_type,
            tags=tags,
            show_nsfw=show_nsfw,
            elo_cut=cut,
        ),
        browsed_collection_id=browsed_collection_id,
    )


@router.get("", response_model=ImagePage)
def get_images(
    cursor: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    q: Listing = Depends(listing),
    db: sqlite3.Connection = Depends(get_db),
) -> ImagePage:
    try:
        return listing_page(
            db,
            q.filters,
            cursor=cursor,
            limit=limit,
            sort=q.sort,
            direction=q.direction,
            elo_collection_id=q.elo_collection_id,
        )
    except InvalidCursor as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/sequence", response_model=list[SequenceItem])
def get_image_sequence(
    q: Listing = Depends(listing),
    db: sqlite3.Connection = Depends(get_db),
) -> list[SequenceItem]:
    """A whole listing in order, for the slideshow: takes the listing's own
    sort and filters, and scores each image in the collection browsed."""
    return sequence(
        db,
        sort=q.sort,
        direction=q.direction,
        elo_collection_id=q.elo_collection_id,
        score_collection_id=q.browsed_collection_id,
        filters=q.filters,
    )


@router.get("/{content_hash}/neighbors", response_model=Neighbors)
def get_image_neighbors(
    content_hash: ContentHash,
    window: int = Query(50, ge=1, le=500),
    q: Listing = Depends(listing),
    db: sqlite3.Connection = Depends(get_db),
) -> Neighbors:
    """The images around one image in a listing, for the viewer's prev/next:
    takes the listing's own sort and filters, and works wherever the image
    falls in it."""
    result = neighbors(
        db,
        content_hash,
        window=window,
        sort=q.sort,
        direction=q.direction,
        elo_collection_id=q.elo_collection_id,
        filters=q.filters,
    )
    if result is None:
        raise HTTPException(404, "Image not found")
    return result


@router.get("/{content_hash}", response_model=ImageDetail)
def get_image_detail(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> ImageDetail:
    image = get_image(db, content_hash)
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


@router.get("/{content_hash}/elo", response_model=list[EloStanding])
def get_image_elo(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> list[EloStanding]:
    """The image's ELO standing in each collection it has been voted in."""
    standings = image_standings(db, content_hash)
    if standings is None:
        raise HTTPException(404, "Image not found")
    return standings


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


@router.get("/{content_hash}/video")
def get_image_video(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
    video_dir: Path = Depends(get_video_dir),
) -> FileResponse:
    """The video as the viewer plays it: its playable copy when it has one
    (made at scan time for what iOS cannot play), else the original."""
    file_path = resolve_file_path(db, content_hash)
    if file_path is None:
        raise HTTPException(404, "Image not found")
    copy = playable_copy_path(video_dir, content_hash)
    try:
        if copy.exists():
            return FileResponse(copy, media_type="video/mp4", headers=IMMUTABLE)
    except OSError:
        logger.exception("Could not check the playable copy %s", copy)
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


@router.get("/{content_hash}/copies", response_model=list[Copy])
def get_image_copies(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> list[Copy]:
    copies = image_copies(db, content_hash)
    if copies is None:
        raise HTTPException(404, "Image not found")
    return copies


class SidecarContent(BaseModel):
    """A sidecar of one copy; `text` is None when it is binary or too large."""

    source_id: int
    relative_path: str
    size: int
    text: Optional[str]


@router.get("/{content_hash}/sidecars", response_model=list[SidecarContent])
def get_image_sidecars(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
) -> list[SidecarContent]:
    """What the sidecars of every copy say, read from disk. A sidecar
    that cannot be read is left out."""
    copies = image_copies(db, content_hash)
    if copies is None:
        raise HTTPException(404, "Image not found")
    contents = []
    for c in copies:
        for relative in c.sidecars:
            path = Path(c.source_path) / relative
            try:
                contents.append(SidecarContent(
                    source_id=c.source_id,
                    relative_path=relative,
                    size=path.stat().st_size,
                    text=text_of(path),
                ))
            except OSError:
                continue
    return contents


class ImageDeleteFailure(BaseModel):
    source_id: int
    relative_path: str
    error: str


class ImageDeletion(BaseModel):
    deleted: int
    sidecars: int
    failed: list[ImageDeleteFailure]


@router.post("/{content_hash}/delete", response_model=ImageDeletion)
def delete_image_files(
    content_hash: ContentHash,
    db: sqlite3.Connection = Depends(get_db),
    video_dir: Path = Depends(get_video_dir),
) -> ImageDeletion:
    """Delete every copy of the image from disk. Refused as a whole if any
    copy may not be deleted."""
    try:
        result = delete_image(db, content_hash)
    except (SourceNotWritable, DeletionRefused) as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Image not found")
    if not result.failed:
        playable_copy_path(video_dir, content_hash).unlink(missing_ok=True)
    return ImageDeletion(
        deleted=len(result.deleted),
        sidecars=len(result.sidecars),
        failed=[
            ImageDeleteFailure(source_id=s, relative_path=p, error=e) for s, p, e in result.failed
        ],
    )
