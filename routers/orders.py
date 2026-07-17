import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

import services
from auth import authorize_store, require_page

router = APIRouter()


class MerchantMappingRequest(BaseModel):
    store_name: str
    product_id: str
    merchant_code: str


@router.get("", response_model=List[Dict[str, Any]])
def list_orders(
    store_name: str = Query(...),
    date: datetime.date = Query(...),
    user: dict = Depends(require_page("orders")),
):
    authorize_store(user, store_name)
    return services.get_orders(store_name, date)


@router.post("/mappings", response_model=Dict[str, Any])
def save_merchant_mapping(
    req: MerchantMappingRequest,
    user: dict = Depends(require_page("orders")),
):
    authorize_store(user, req.store_name)
    return services.save_merchant_mapping(req.store_name, req.product_id, req.merchant_code)
