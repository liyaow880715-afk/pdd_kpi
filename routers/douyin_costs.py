import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

import douyin_cost_manager
import douyin_services
from auth import accessible_stores, get_current_user, require_page
from store_manager import list_store_names

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def list_costs(user: dict = Depends(require_page("douyin_costs"))):
    return douyin_cost_manager.get_costs()


@router.post("", response_model=Dict[str, Any])
def save_costs(
    costs: List[Dict[str, Any]],
    user: dict = Depends(require_page("douyin_costs")),
):
    douyin_cost_manager.save_costs(costs)
    return {"saved": True}


@router.get("/export")
def export_costs(user: dict = Depends(require_page("douyin_costs"))):
    data = douyin_cost_manager.export_costs_to_csv()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=douyin_costs.csv"},
    )


@router.post("/import", response_model=Dict[str, Any])
def import_costs(
    file: UploadFile = File(...),
    user: dict = Depends(require_page("douyin_costs")),
):
    file_bytes = file.file.read()
    return douyin_cost_manager.import_costs_from_csv(file_bytes)


@router.get("/unmapped", response_model=List[Dict[str, Any]])
def unmapped_products(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    store_name: Optional[str] = Query(None),
    user: dict = Depends(require_page("douyin_costs")),
):
    allowed = accessible_stores(user, list_store_names("douyin"))
    store_names = [store_name] if store_name and store_name in allowed else allowed

    product_dfs = []
    for store in store_names:
        analysis = douyin_services.load_douyin_analysis(store, start_date, end_date)
        product_dfs.extend(analysis.get("product_metrics", []))

    if not product_dfs:
        return []

    import pandas as pd

    df = pd.DataFrame(product_dfs)
    return douyin_cost_manager.get_unmapped_products(df)
