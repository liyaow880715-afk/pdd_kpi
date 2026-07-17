import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

import services
from auth import accessible_stores, authorize_stores, require_page
from store_manager import list_store_names

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def dashboard_summary(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    store_names: Optional[List[str]] = Query(None),
    user: dict = Depends(require_page("overview")),
):
    allowed = accessible_stores(user, list_store_names("pdd"))
    if store_names:
        selected = authorize_stores(user, store_names)
    else:
        selected = allowed
    return services.get_dashboard_summary(start_date, end_date, store_names=selected)
