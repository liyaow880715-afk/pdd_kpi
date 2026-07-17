import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

import douyin_services
from auth import get_current_user, require_master, require_page

router = APIRouter()


@router.get("/config", response_model=Dict[str, Any])
def get_config(user: dict = Depends(require_page("ai_wecom"))):
    return douyin_services.get_douyin_wecom_config()


@router.post("/config", response_model=Dict[str, Any])
def update_config(
    config: Dict[str, Any],
    user: dict = Depends(require_master),
):
    return douyin_services.update_douyin_wecom_config(config)


@router.post("/send", response_model=Dict[str, Any])
def send_report(
    report_date: datetime.date,
    config: Dict[str, Any],
    user: dict = Depends(require_page("ai_wecom")),
):
    return douyin_services.send_douyin_wecom_report(report_date, config)
