import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

import douyin_services
from auth import authorize_store, get_current_user, require_master, require_page

router = APIRouter()


@router.get("/config", response_model=Dict[str, Any])
def get_config(user: dict = Depends(require_page("ai_wecom"))):
    return douyin_services.get_douyin_ai_config()


@router.post("/config", response_model=Dict[str, Any])
def update_config(
    config: Dict[str, Any],
    user: dict = Depends(require_master),
):
    return douyin_services.update_douyin_ai_config(config)


@router.post("/test", response_model=Dict[str, Any])
def test_ai(
    config: Dict[str, Any],
    user: dict = Depends(require_page("ai_wecom")),
):
    try:
        reply = douyin_services.test_douyin_ai(config)
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/report", response_model=Dict[str, Any])
def generate_report(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    config: Dict[str, Any],
    user: dict = Depends(require_page("ai_wecom")),
):
    authorize_store(user, store_name)
    return douyin_services.generate_douyin_ai_report(store_name, start_date, end_date, config)
