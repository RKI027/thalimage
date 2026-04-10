"""Collection management endpoints."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from thalimage.deps import get_db
from thalimage.services.collection_service import (
    Collection,
    add_images,
    create_collection,
    delete_collection,
    get_collection,
    list_collections,
    remove_images,
    update_collection,
)

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    sort_by: Optional[str] = None
    sort_dir: Optional[str] = None


class CollectionImagesBody(BaseModel):
    hashes: list[str]


@router.get("", response_model=list[Collection])
def get_collections(
    type: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
) -> list[Collection]:
    return list_collections(db, type=type)


@router.post("", response_model=Collection, status_code=201)
def post_collection(
    body: CollectionCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> Collection:
    return create_collection(db, body.name, body.parent_id)


@router.get("/{collection_id}", response_model=Collection)
def get_collection_detail(
    collection_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> Collection:
    coll = get_collection(db, collection_id)
    if coll is None:
        raise HTTPException(404, "Collection not found")
    return coll


@router.patch("/{collection_id}", response_model=Collection)
def patch_collection(
    collection_id: int,
    body: CollectionUpdate,
    db: sqlite3.Connection = Depends(get_db),
) -> Collection:
    result = update_collection(
        db, collection_id,
        name=body.name,
        sort_by=body.sort_by,
        sort_dir=body.sort_dir,
    )
    if result is None:
        raise HTTPException(404, "Collection not found")
    if isinstance(result, str):
        raise HTTPException(403, "Cannot rename a preset collection")
    return result


@router.delete("/{collection_id}", status_code=204)
def del_collection(
    collection_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    result = delete_collection(db, collection_id)
    if isinstance(result, str):
        raise HTTPException(403, "Cannot delete a preset collection")
    if not result:
        raise HTTPException(404, "Collection not found")


@router.post("/{collection_id}/images")
def post_collection_images(
    collection_id: int,
    body: CollectionImagesBody,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, int]:
    coll = get_collection(db, collection_id)
    if coll is None:
        raise HTTPException(404, "Collection not found")
    added = add_images(db, collection_id, body.hashes)
    return {"added": added}


@router.delete("/{collection_id}/images")
def del_collection_images(
    collection_id: int,
    body: CollectionImagesBody,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, int]:
    removed = remove_images(db, collection_id, body.hashes)
    return {"removed": removed}
