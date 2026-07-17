import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import wechat_cost_manager
import wechat_services
from auth import accessible_stores, get_current_user, require_page
from services import bump_data_version
from store_manager import list_store_names

router = APIRouter()


class CostRecord(BaseModel):
    sku_code: str
    product_name: str = ""
    product_cost: float = 0.0
    logistics_cost: float = 0.0


class SaveCostsRequest(BaseModel):
    costs: List[CostRecord]


class ProductMappingRequest(BaseModel):
    product_id: str
    sku_code: str
    product_name: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
def list_costs(_: dict = Depends(require_page("wechat_costs"))):
    return wechat_cost_manager.get_costs()


@router.post("", response_model=Dict[str, Any])
def save_costs(
    req: SaveCostsRequest,
    _: dict = Depends(require_page("wechat_costs")),
):
    wechat_cost_manager.save_costs([c.model_dump() for c in req.costs])
    bump_data_version()
    return {"saved": True}


@router.get("/export", response_class=PlainTextResponse)
def export_costs(
    pending_only: bool = False,
    _: dict = Depends(require_page("wechat_costs")),
):
    return wechat_cost_manager.export_costs_to_csv(pending_only)


@router.post("/import", response_model=Dict[str, Any])
def import_costs(
    file: UploadFile = File(...),
    _: dict = Depends(require_page("wechat_costs")),
):
    file_bytes = file.file.read()
    count = wechat_cost_manager.import_costs_from_csv(file_bytes)
    bump_data_version()
    return {"updated": count}


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_cost_codes(_: dict = Depends(require_page("wechat_costs"))):
    result = wechat_cost_manager.refresh_cost_codes()
    bump_data_version()
    return result


@router.get("/unmapped", response_model=List[Dict[str, Any]])
def unmapped_products(
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    store_name: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    allowed = accessible_stores(user, list_store_names("wechat"))
    store_names = [store_name] if store_name and store_name in allowed else allowed

    start_s = start_date.strftime("%Y-%m-%d") if start_date else None
    end_s = end_date.strftime("%Y-%m-%d") if end_date else None
    return wechat_cost_manager.get_products_without_cost(
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
    allowed = accessible_stores(user, list_store_names("wechat"))
    store_names = [store_name] if store_name and store_name in allowed else allowed

    start_s = start_date.strftime("%Y-%m-%d") if start_date else None
    end_s = end_date.strftime("%Y-%m-%d") if end_date else None
    # 微信小店：有 SKU 编码但成本未维护 -> 红色待维护；SKU 编码为空 -> 绿色未映射
    config = wechat_cost_manager.load_cost_config()
    costs = wechat_cost_manager._get_costs_dict(config)

    pending_codes: set = set()
    unmapped_keys: set = set()

    stores = store_names if store_names else wechat_cost_manager.list_wechat_stores()
    for store in stores:
        dates = wechat_cost_manager.list_available_dates(store)
        if start_date and end_date:
            start_s = start_date.strftime("%Y-%m-%d")
            end_s = end_date.strftime("%Y-%m-%d")
            dates = [d for d in dates if start_s <= d <= end_s]
        for d in dates:
            try:
                orders = wechat_cost_manager.load_daily_orders(store, d)
                if orders.empty or "sku_code" not in orders.columns:
                    continue
                for _, r in orders.iterrows():
                    code = wechat_cost_manager._normalize_code(r.get("sku_code"))
                    if not code:
                        key = (
                            str(r.get("product_name", "") or "").strip()
                            or str(r.get("platform_sku_code", "") or "").strip()
                        )
                        if key:
                            unmapped_keys.add(key)
                        continue
                    cost = costs.get(code)
                    if (
                        not cost
                        or cost.get("product_cost", 0) <= 0
                        or cost.get("logistics_cost", 0) <= 0
                    ):
                        pending_codes.add(code)
            except Exception:
                continue

    return {"pending": len(pending_codes), "unmapped": len(unmapped_keys)}


@router.post("/map", response_model=Dict[str, Any])
def map_product_to_sku_code(
    req: ProductMappingRequest,
    _: dict = Depends(require_page("wechat_costs")),
):
    cfg = wechat_cost_manager.load_cost_config()
    cfg = wechat_cost_manager.set_cost(
        cfg,
        sku_code=req.sku_code,
        product_name=req.product_name or "",
    )
    wechat_cost_manager.save_cost_config(cfg)
    bump_data_version()
    return {"product_id": req.product_id, "sku_code": req.sku_code}
