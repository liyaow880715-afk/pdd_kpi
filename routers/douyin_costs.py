import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import douyin_cost_manager
import douyin_services
from auth import accessible_stores, get_current_user, require_page
from store_manager import list_store_names
from services import bump_data_version

router = APIRouter()


class CostRecord(BaseModel):
    merchant_code: str
    product_name: str = ""
    product_cost: float = 0.0
    logistics_cost: float = 0.0


class SaveCostsRequest(BaseModel):
    costs: List[CostRecord]


class ProductMappingRequest(BaseModel):
    product_id: str
    merchant_code: str
    style_id: Optional[str] = None
    product_name: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
def list_costs(_: dict = Depends(require_page("douyin_costs"))):
    return douyin_cost_manager.get_global_costs()


@router.post("", response_model=Dict[str, Any])
def save_costs(
    req: SaveCostsRequest,
    _: dict = Depends(require_page("douyin_costs")),
):
    douyin_cost_manager.save_global_costs([c.model_dump() for c in req.costs])
    bump_data_version()
    return {"saved": True}


@router.get("/export", response_class=PlainTextResponse)
def export_costs(
    pending_only: bool = False,
    _: dict = Depends(require_page("douyin_costs")),
):
    return douyin_cost_manager.export_global_costs_to_csv(pending_only)


@router.post("/import", response_model=Dict[str, Any])
def import_costs(
    file: UploadFile = File(...),
    _: dict = Depends(require_page("douyin_costs")),
):
    file_bytes = file.file.read()
    count = douyin_cost_manager.import_global_costs_from_csv(file_bytes)
    bump_data_version()
    return {"updated": count}


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_cost_codes(_: dict = Depends(require_page("douyin_costs"))):
    result = douyin_cost_manager.refresh_global_cost_codes()
    bump_data_version()
    return result


@router.get("/unmapped", response_model=List[Dict[str, Any]])
def unmapped_products(
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    store_name: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    allowed = accessible_stores(user, list_store_names("douyin"))
    store_names = [store_name] if store_name and store_name in allowed else allowed

    start_s = start_date.strftime("%Y-%m-%d") if start_date else None
    end_s = end_date.strftime("%Y-%m-%d") if end_date else None
    return douyin_cost_manager.get_products_without_merchant_code(
        store_names=store_names,
        start_date=start_s,
        end_date=end_s,
    ).to_dict("records")


@router.get("/unmapped/count", response_model=Dict[str, int])
def count_unmapped_products(
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    store_name: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    allowed = accessible_stores(user, list_store_names("douyin"))
    store_names = [store_name] if store_name and store_name in allowed else allowed

    start_s = start_date.strftime("%Y-%m-%d") if start_date else None
    end_s = end_date.strftime("%Y-%m-%d") if end_date else None
    df = douyin_cost_manager.get_products_without_merchant_code(
        store_names=store_names,
        start_date=start_s,
        end_date=end_s,
    )
    unmapped = len(df)
    pending = sum(
        1
        for c in douyin_cost_manager.get_global_costs()
        if c.get("product_cost", 0) <= 0 or c.get("logistics_cost", 0) <= 0
    )
    return {"count": unmapped + pending}


@router.post("/map", response_model=Dict[str, Any])
def map_product_to_merchant_code(
    req: ProductMappingRequest,
    _: dict = Depends(require_page("douyin_costs")),
):
    cfg = douyin_cost_manager.load_cost_config()
    cfg = douyin_cost_manager.save_global_product_mapping(
        cfg,
        req.product_id,
        req.merchant_code,
        style_id=req.style_id,
        product_name=req.product_name or "",
    )
    douyin_cost_manager.save_cost_config(cfg)
    bump_data_version()
    return {"product_id": req.product_id, "style_id": req.style_id, "merchant_code": req.merchant_code}
