import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

import services
from auth import authorize_store, authorize_stores, require_page

router = APIRouter()


@router.get("/analysis", response_model=Dict[str, Any])
def analysis(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(require_page("metrics")),
):
    authorize_store(user, store_name)
    return services.load_analysis_data(store_name, start_date, end_date)


@router.get("/trend", response_model=List[Dict[str, Any]])
def trend(
    store_names: List[str] = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(require_page("metrics")),
):
    allowed = authorize_stores(user, store_names)
    if not allowed:
        return []
    return services.load_trend_data(allowed, start_date, end_date)
