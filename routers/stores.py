from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import services
from auth import accessible_stores, get_current_user

router = APIRouter()


class CreateStoreRequest(BaseModel):
    name: str
    platform: str = "pdd"


class RenameStoreRequest(BaseModel):
    new_name: str


@router.get("", response_model=List[Dict[str, Any]])
def list_stores(
    platform: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    all_stores = services.get_stores(platform=platform)
    allowed_names = set(accessible_stores(user, [s["name"] for s in all_stores]))
    return [s for s in all_stores if s["name"] in allowed_names]


@router.post("", response_model=Dict[str, Any])
def create_store(req: CreateStoreRequest, _: dict = Depends(get_current_user)):
    return services.create_store(req.name, platform=req.platform)


@router.patch("/{store_id}", response_model=Dict[str, Any])
def rename_store(store_id: str, req: RenameStoreRequest, _: dict = Depends(get_current_user)):
    store = services.rename_store_service(store_id, req.new_name)
    if not store:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return store


@router.delete("/{store_id}")
def delete_store(store_id: str, _: dict = Depends(get_current_user)):
    ok = services.delete_store_service(store_id)
    if not ok:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return {"deleted": True}
