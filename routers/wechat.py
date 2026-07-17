import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

import wechat_services
from auth import authorize_store, accessible_stores, get_current_user, require_page
from store_manager import list_store_names

router = APIRouter()


@router.post("/import", response_model=Dict[str, Any])
def import_wechat_data(
    store_name: str = Form(...),
    import_date: Optional[datetime.date] = Form(None),
    order_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    if not order_file:
        return {"error": "请上传订单数据"}
    order_bytes = order_file.file.read()
    return wechat_services.import_wechat_daily_data(
        store_name=store_name,
        import_date=import_date,
        order_bytes=order_bytes,
        order_filename=order_file.filename,
    )


@router.get("/analysis", response_model=Dict[str, Any])
def analysis(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return wechat_services.load_wechat_analysis(store_name, start_date, end_date)


@router.get("/trend", response_model=List[Dict[str, Any]])
def trend(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return wechat_services.load_wechat_trend(store_name, start_date, end_date)


@router.get("/dashboard", response_model=Dict[str, Any])
def dashboard_summary(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    store_names: Optional[List[str]] = Query(None),
    user: dict = Depends(require_page("wechat")),
):
    allowed = accessible_stores(user, list_store_names("wechat"))
    if store_names:
        selected = [s for s in store_names if s in allowed]
    else:
        selected = allowed
    return wechat_services.get_wechat_dashboard_summary(start_date, end_date, store_names=selected)


@router.get("/orders", response_model=List[Dict[str, Any]])
def list_orders(
    store_name: str = Query(...),
    date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return wechat_services.get_wechat_orders(store_name, date)


@router.get("/records", response_model=List[Dict[str, Any]])
def list_records(
    store_name: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    if user.get("role") == "master":
        return wechat_services.get_wechat_records(store_name)
    allowed = set(user.get("allowed_stores") or [])
    records = wechat_services.get_wechat_records(store_name)
    return [r for r in records if r.get("store_name") in allowed]


@router.delete("/records/{store_name}/{date}", response_model=Dict[str, Any])
def delete_record(
    store_name: str,
    date: datetime.date,
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return wechat_services.delete_wechat_record(store_name, date)


@router.get("/kol-stats", response_model=List[Dict[str, Any]])
def kol_stats(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    user: dict = Depends(get_current_user),
):
    authorize_store(user, store_name)
    return wechat_services.get_kol_stats(store_name, start_date, end_date)
