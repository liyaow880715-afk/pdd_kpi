import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

import tmall_services
from auth import authorize_store, accessible_stores, get_current_user, require_page
from store_manager import list_store_names

router = APIRouter()


@router.post("/import", response_model=Dict[str, Any])
def import_tmall_data(
    store_name: str = Form(...),
    import_date: Optional[datetime.date] = Form(None),
    promo_file: Optional[UploadFile] = File(None),
    order_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    if not promo_file and not order_file:
        return {"error": "请至少上传推广数据或订单数据中的一个"}
    promo_bytes = promo_file.file.read() if promo_file else None
    order_bytes = order_file.file.read() if order_file else None
    return tmall_services.import_tmall_daily_data(
        store_name=store_name,
        import_date=import_date,
        promo_bytes=promo_bytes,
        promo_filename=promo_file.filename if promo_file else None,
        order_bytes=order_bytes,
        order_filename=order_file.filename if order_file else None,
    )


@router.get("/analysis", response_model=Dict[str, Any])
def analysis(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return tmall_services.load_tmall_analysis(store_name, start_date, end_date)


@router.get("/trend", response_model=List[Dict[str, Any]])
def trend(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return tmall_services.load_tmall_trend(store_name, start_date, end_date)


@router.get("/dashboard", response_model=Dict[str, Any])
def dashboard_summary(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    store_names: Optional[List[str]] = Query(None),
    user: dict = Depends(require_page("tmall")),
):
    allowed = accessible_stores(user, list_store_names("tmall"))
    if store_names:
        selected = [s for s in store_names if s in allowed]
    else:
        selected = allowed
    return tmall_services.get_tmall_dashboard_summary(start_date, end_date, store_names=selected)


@router.get("/orders", response_model=List[Dict[str, Any]])
def list_orders(
    store_name: str = Query(...),
    date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return tmall_services.get_tmall_orders(store_name, date)


@router.get("/records", response_model=List[Dict[str, Any]])
def list_records(
    store_name: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "master":
        return tmall_services.get_tmall_records(store_name)
    allowed = set(user.get("allowed_stores") or [])
    records = tmall_services.get_tmall_records(store_name)
    return [r for r in records if r.get("store_name") in allowed]


@router.delete("/records/{store_name}/{date}", response_model=Dict[str, Any])
def delete_record(
    store_name: str,
    date: datetime.date,
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return tmall_services.delete_tmall_record(store_name, date)
