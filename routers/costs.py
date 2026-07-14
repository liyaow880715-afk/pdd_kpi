from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import services

router = APIRouter()


class CostRecord(BaseModel):
    merchant_code: str
    product_name: str = ""
    product_cost: float = 0.0
    logistics_cost: float = 0.0


class SaveCostsRequest(BaseModel):
    store_name: str
    costs: List[CostRecord]


class SaveGlobalCostsRequest(BaseModel):
    costs: List[CostRecord]


class ProductMappingRequest(BaseModel):
    product_id: str
    merchant_code: str
    style_id: Optional[str] = None


# ---------- 按店铺（旧接口，保留兼容） ----------

@router.get("", response_model=List[Dict[str, Any]])
def list_costs(store_name: str):
    return services.get_costs(store_name)


@router.post("", response_model=Dict[str, Any])
def save_costs(req: SaveCostsRequest):
    return services.save_costs(req.store_name, [c.model_dump() for c in req.costs])


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_cost_codes(store_name: str):
    return services.refresh_cost_codes(store_name)


@router.get("/export", response_class=PlainTextResponse)
def export_costs(store_name: str):
    return services.export_cost_csv(store_name)


@router.post("/import", response_model=Dict[str, Any])
def import_costs(store_name: str = Form(...), file: UploadFile = File(...)):
    file_bytes = file.file.read()
    return services.import_cost_csv(store_name, file_bytes)


# ---------- 全局成本（不区分店铺） ----------

@router.get("/global", response_model=List[Dict[str, Any]])
def list_global_costs():
    return services.get_global_costs()


@router.post("/global", response_model=Dict[str, Any])
def save_global_costs(req: SaveGlobalCostsRequest):
    return services.save_global_costs([c.model_dump() for c in req.costs])


@router.post("/global/refresh", response_model=Dict[str, Any])
def refresh_global_cost_codes():
    return services.refresh_global_cost_codes_service()


@router.get("/global/unmapped", response_model=List[Dict[str, Any]])
def list_unmapped_products():
    return services.get_unmapped_products()


@router.post("/global/map", response_model=Dict[str, Any])
def map_product_to_merchant_code(req: ProductMappingRequest):
    return services.save_global_product_mapping_service(req.product_id, req.merchant_code, style_id=req.style_id)
