import datetime

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

import services

router = APIRouter()


@router.get("/products", response_class=PlainTextResponse)
def export_products(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
):
    return services.export_product_metrics_csv(store_name, start_date, end_date)


@router.get("/styles", response_class=PlainTextResponse)
def export_styles(
    store_name: str = Query(...),
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
):
    return services.export_style_metrics_csv(store_name, start_date, end_date)
