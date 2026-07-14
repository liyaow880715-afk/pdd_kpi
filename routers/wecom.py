import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

import services

router = APIRouter()


class ListenRequest(BaseModel):
    config: Dict[str, Any]
    timeout: int = 60


class SendReportRequest(BaseModel):
    report_date: datetime.date
    config: Dict[str, Any]


@router.get("/config", response_model=Dict[str, Any])
def get_config():
    return services.get_wecom_config()


@router.post("/config", response_model=Dict[str, Any])
def update_config(config: Dict[str, Any]):
    return services.update_wecom_config(config)


@router.post("/listen", response_model=Optional[str])
def listen(req: ListenRequest):
    return services.listen_wecom(req.config, req.timeout)


@router.post("/send", response_model=Dict[str, Any])
def send_report(req: SendReportRequest):
    return services.send_wecom_report_service(req.report_date, req.config)
