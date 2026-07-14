import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, UploadFile

import services

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
def import_daily_data(
    store_name: str = Form(...),
    import_date: datetime.date = Form(...),
    promo_file: Optional[UploadFile] = File(None),
    order_file: Optional[UploadFile] = File(None),
):
    if not promo_file and not order_file:
        return {"error": "请至少上传推广数据或订单数据中的一个"}
    promo_bytes = promo_file.file.read() if promo_file else None
    order_bytes = order_file.file.read() if order_file else None
    return services.import_daily_data(
        store_name=store_name,
        import_date=import_date,
        promo_bytes=promo_bytes,
        promo_filename=promo_file.filename or "promo.xlsx" if promo_file else None,
        order_bytes=order_bytes,
        order_filename=order_file.filename or "order.csv" if order_file else None,
    )


@router.get("/records", response_model=List[Dict[str, Any]])
def list_records(store_name: Optional[str] = None):
    return services.get_records(store_name)


@router.delete("/records/{store_name}/{date}", response_model=Dict[str, Any])
def delete_record(store_name: str, date: datetime.date):
    return services.delete_record(store_name, date)
