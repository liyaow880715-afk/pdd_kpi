import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, UploadFile

import services

router = APIRouter()


@router.post("", response_model=Dict[str, Any])
def import_daily_data(
    store_name: str = Form(...),
    import_date: datetime.date = Form(...),
    promo_file: UploadFile = File(...),
    order_file: UploadFile = File(...),
):
    promo_bytes = promo_file.file.read()
    order_bytes = order_file.file.read()
    return services.import_daily_data(
        store_name=store_name,
        import_date=import_date,
        promo_bytes=promo_bytes,
        promo_filename=promo_file.filename or "promo.xlsx",
        order_bytes=order_bytes,
        order_filename=order_file.filename or "order.csv",
    )


@router.get("/records", response_model=List[Dict[str, Any]])
def list_records(store_name: Optional[str] = None):
    return services.get_records(store_name)


@router.delete("/records/{store_name}/{date}", response_model=Dict[str, Any])
def delete_record(store_name: str, date: datetime.date):
    return services.delete_record(store_name, date)
