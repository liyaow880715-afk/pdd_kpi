import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

import services
from auth import authorize_store, require_page
from helpers import read_upload_file

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
def import_daily_data(
    store_name: str = Form(...),
    import_date: datetime.date = Form(...),
    promo_file: Optional[UploadFile] = File(None),
    order_file: Optional[UploadFile] = File(None),
    user: dict = Depends(require_page("import")),
):
    authorize_store(user, store_name)
    if not promo_file and not order_file:
        return {"error": "请至少上传推广数据或订单数据中的一个"}
    promo_bytes = read_upload_file(promo_file) if promo_file else None
    order_bytes = read_upload_file(order_file) if order_file else None
    return services.import_daily_data(
        store_name=store_name,
        import_date=import_date,
        promo_bytes=promo_bytes,
        promo_filename=promo_file.filename or "promo.xlsx" if promo_file else None,
        order_bytes=order_bytes,
        order_filename=order_file.filename or "order.csv" if order_file else None,
    )


@router.get("/records", response_model=List[Dict[str, Any]])
def list_records(
    store_name: Optional[str] = None,
    user: dict = Depends(require_page("import")),
):
    records = services.get_records(store_name)
    allowed_names = set(user.get("allowed_stores") or [])
    if user.get("role") == "master":
        return records
    return [r for r in records if r.get("store_name") in allowed_names]


@router.delete("/records/{store_name}/{date}", response_model=Dict[str, Any])
def delete_record(
    store_name: str,
    date: datetime.date,
    user: dict = Depends(require_page("import")),
):
    authorize_store(user, store_name)
    return services.delete_record(store_name, date)
