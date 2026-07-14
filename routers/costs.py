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
