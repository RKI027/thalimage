"""ELO voting endpoints."""

import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from thalimage.deps import get_db
from thalimage.services.collection_service import get_collection
from thalimage.services.elo_service import get_pair, get_rankings, record_vote
from thalimage.services.image_service import ImageSummary

router = APIRouter(prefix="/collections/{collection_id}/elo", tags=["elo"])


class EloPairResponse(BaseModel):
    left: ImageSummary
    right: ImageSummary


class VoteRequest(BaseModel):
    winner_hash: str
    loser_hash: str


@router.get("/pair", response_model=EloPairResponse)
def get_elo_pair(
    collection_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    aspect_ratio_filter: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    db: sqlite3.Connection = Depends(get_db),
) -> EloPairResponse:
    # Source preset collections are served dynamically via source_id (no collection_images rows).
    source_id: Optional[int] = None
    coll = get_collection(db, collection_id)
    if coll is not None and coll.type == "source_preset":
        source_id = coll.source_id

    try:
        left, right = get_pair(
            db,
            collection_id,
            source_id=source_id,
            date_from=date_from,
            date_to=date_to,
            aspect_ratio_filter=aspect_ratio_filter,
            media_type=media_type,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return EloPairResponse(left=left, right=right)


@router.post("/vote", status_code=201)
def post_vote(
    collection_id: int,
    body: VoteRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    try:
        record_vote(
            db, collection_id,
            winner_hash=body.winner_hash,
            loser_hash=body.loser_hash,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "recorded"}


@router.get("/rankings")
def get_elo_rankings(
    collection_id: int,
    limit: int = 100,
    db: sqlite3.Connection = Depends(get_db),
) -> list[dict[str, Any]]:
    return get_rankings(db, collection_id, limit=limit)
