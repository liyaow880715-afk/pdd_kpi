from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import services

router = APIRouter()


class CreateStoreRequest(BaseModel):
    name: str


class RenameStoreRequest(BaseModel):
    new_name: str


@router.get("", response_model=List[Dict[str, Any]])
def list_stores():
    return services.get_stores()


@router.post("", response_model=Dict[str, Any])
def create_store(req: CreateStoreRequest):
    return services.create_store(req.name)


@router.patch("/{store_id}", response_model=Dict[str, Any])
def rename_store(store_id: str, req: RenameStoreRequest):
    store = services.rename_store_service(store_id, req.new_name)
    if not store:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return store


@router.delete("/{store_id}")
def delete_store(store_id: str):
    ok = services.delete_store_service(store_id)
    if not ok:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return {"deleted": True}
