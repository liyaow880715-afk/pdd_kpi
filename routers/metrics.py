import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Query

import services

router = APIRouter()


@router.get("/analysis", response_model=Dict[str, Any])
def analysis(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
):
    return services.load_analysis_data(store_name, start_date, end_date)


@router.get("/trend", response_model=List[Dict[str, Any]])
def trend(
    store_names: List[str] = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
):
    return services.load_trend_data(store_names, start_date, end_date)
