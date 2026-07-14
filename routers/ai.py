import datetime
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

import services

router = APIRouter()


class AIReportRequest(BaseModel):
    store_name: str
    start_date: datetime.date
    end_date: datetime.date
    config: Dict[str, Any]


@router.get("/config", response_model=Dict[str, Any])
def get_config():
    return services.get_ai_config()


@router.post("/config", response_model=Dict[str, Any])
def update_config(config: Dict[str, Any]):
    return services.update_ai_config(config)


@router.post("/test", response_model=Dict[str, Any])
def test_ai(config: Dict[str, Any]):
    return services.test_ai_service(config)


@router.post("/report", response_model=Dict[str, Any])
def generate_report(req: AIReportRequest):
    return services.generate_ai_report_service(
        req.store_name, req.start_date, req.end_date, req.config
    )
