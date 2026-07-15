import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

import services
from auth import accessible_stores, get_current_user
from store_manager import list_store_names

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def dashboard_summary(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    allowed = accessible_stores(user, list_store_names())
    return services.get_dashboard_summary(start_date, end_date, store_names=allowed)
