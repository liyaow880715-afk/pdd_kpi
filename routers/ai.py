import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import services
from auth import authorize_store, get_current_user, require_master, require_page

router = APIRouter()


class AIReportRequest(BaseModel):
    store_name: str
    start_date: datetime.date
    end_date: datetime.date
    config: Dict[str, Any]


@router.get("/config", response_model=Dict[str, Any])
def get_config(_: dict = Depends(require_page("ai_wecom"))):
    return services.get_ai_config()


@router.post("/config", response_model=Dict[str, Any])
def update_config(
    config: Dict[str, Any],
    _: dict = Depends(require_master),
):
    return services.update_ai_config(config)


@router.post("/test", response_model=Dict[str, Any])
def test_ai(
    config: Dict[str, Any],
    _: dict = Depends(require_page("ai_wecom")),
):
    return services.test_ai_service(config)


@router.post("/report", response_model=Dict[str, Any])
def generate_report(
    req: AIReportRequest,
    user: dict = Depends(get_current_user),
):
    authorize_store(user, req.store_name)
    return services.generate_ai_report_service(
        req.store_name, req.start_date, req.end_date, req.config
    )
