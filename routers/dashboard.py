import datetime
from typing import Any, Dict

from fastapi import APIRouter, Query

import services

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def dashboard_summary(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
):
    return services.get_dashboard_summary(start_date, end_date)
