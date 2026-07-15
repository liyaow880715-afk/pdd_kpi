"""
抖音业务服务层
"""

import datetime
import json as _json
from pathlib import Path as _Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import wecom as wecom_sender

from douyin_loader import read_order_file, read_promotion_file
from douyin_metrics import aggregate_product_metrics, compute_overall_kpis
from douyin_cost_manager import apply_costs_to_metrics, compute_cost_kpis
from douyin_storage import (
    delete_daily_data,
    list_available_dates,
    list_douyin_records,
    load_daily_data,
    save_daily_data,
)
from services import bump_data_version


def _date_str(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if pd.isna(obj):
        return None
    return obj


def import_douyin_daily_data(
    store_name: str,
    import_date: Optional[datetime.date] = None,
    promo_bytes: Optional[bytes] = None,
    promo_filename: Optional[str] = None,
    order_bytes: Optional[bytes] = None,
    order_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """导入抖音每日数据。

    支持两种文件：
    - 单日文件：只包含一个日期，按该日期保存。
    - 全数据文件：包含多个日期，自动按日期拆分保存。
    """
    processed_dates: set = set()
    total_product_rows = 0
    total_order_rows = 0

    if promo_bytes:
        promo_df = read_promotion_file(promo_bytes, promo_filename or "promo.xlsx")
        if not promo_df.empty:
            # 如果指定了日期且文件里有该日期，优先按指定日期处理；否则处理文件内所有日期
            promo_dates = promo_df["date"].dropna().unique()
            if import_date and _date_str(import_date) in promo_dates:
                promo_dates = [_date_str(import_date)]
            for d in promo_dates:
                day_df = promo_df[promo_df["date"] == d]
                if day_df.empty:
                    continue
                existing_orders = load_daily_data(store_name, d)[1]
                meta = {
                    "promo_file": promo_filename or "",
                    "order_file": order_filename or "",
                    "product_rows": len(day_df),
                    "order_rows": len(existing_orders),
                    "saved_at": datetime.datetime.now().isoformat(),
                }
                save_daily_data(store_name, d, day_df, existing_orders, meta=meta)
                processed_dates.add(d)
                total_product_rows += len(day_df)

    if order_bytes:
        order_df = read_order_file(order_bytes, order_filename or "order.csv")
        if not order_df.empty:
            order_dates = order_df["order_date"].dropna().unique()
            if import_date and _date_str(import_date) in order_dates:
                order_dates = [_date_str(import_date)]
            for d in order_dates:
                day_orders = order_df[order_df["order_date"] == d]
                if day_orders.empty:
                    continue
                existing_product = load_daily_data(store_name, d)[0]
                meta = {
                    "promo_file": promo_filename or "",
                    "order_file": order_filename or "",
                    "product_rows": len(existing_product),
                    "order_rows": len(day_orders),
                    "saved_at": datetime.datetime.now().isoformat(),
                }
                save_daily_data(store_name, d, existing_product, day_orders, meta=meta)
                processed_dates.add(d)
                total_order_rows += len(day_orders)

    bump_data_version()

    return {
        "store_name": store_name,
        "date": _date_str(import_date) if import_date else None,
        "processed_dates": sorted(processed_dates),
        "product_rows": total_product_rows,
        "order_rows": total_order_rows,
    }


def load_douyin_analysis(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    product_dfs = []
    for d in dates:
        p, _ = load_daily_data(store_name, d)
        if not p.empty:
            product_dfs.append(p)

    product_metrics = aggregate_product_metrics(product_dfs)
    product_metrics = apply_costs_to_metrics(product_metrics)
    overall = compute_overall_kpis(product_metrics)
    cost_kpis = compute_cost_kpis(product_metrics)

    return _json_safe({
        "product_metrics": product_metrics.replace({pd.NA: None, float("nan"): None}).to_dict("records"),
        "kpis": overall,
        "cost_kpis": cost_kpis,
    })


def load_douyin_trend(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> List[Dict[str, Any]]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    rows = []
    for d in dates:
        p, _ = load_daily_data(store_name, d)
        p_cost = apply_costs_to_metrics(p)
        kpis = compute_overall_kpis(p)
        cost = compute_cost_kpis(p_cost)
        row = {"date": d, **kpis, **cost}
        rows.append(_json_safe(row))
    return rows


def get_douyin_dashboard_summary(
    start_date: datetime.date,
    end_date: datetime.date,
    store_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from douyin_storage import list_douyin_stores

    if store_names is None:
        store_names = list_douyin_stores()

    start_s = _date_str(start_date)
    end_s = _date_str(end_date)

    all_product_dfs: List[pd.DataFrame] = []
    daily_dfs: Dict[str, List[pd.DataFrame]] = {}
    for store in store_names:
        for d in list_available_dates(store):
            if start_s <= d <= end_s:
                p, _ = load_daily_data(store, d)
                if not p.empty:
                    all_product_dfs.append(p)
                    daily_dfs.setdefault(d, []).append(p)

    combined = pd.concat(all_product_dfs, ignore_index=True) if all_product_dfs else pd.DataFrame()
    combined_cost = apply_costs_to_metrics(combined)
    overall = compute_overall_kpis(combined)
    cost_kpis = compute_cost_kpis(combined_cost)

    trend_summary = []
    for d in sorted(daily_dfs.keys()):
        day_df = pd.concat(daily_dfs[d], ignore_index=True)
        day_cost = apply_costs_to_metrics(day_df)
        kpis = compute_overall_kpis(day_df)
        cost = compute_cost_kpis(day_cost)
        trend_summary.append(_json_safe({"date": d, **kpis, **cost}))

    return _json_safe({
        "store_count": len(store_names),
        "kpis": overall,
        "cost_kpis": cost_kpis,
        "trend": trend_summary,
    })


def get_douyin_orders(store_name: str, date: datetime.date) -> List[Dict[str, Any]]:
    _, orders = load_daily_data(store_name, _date_str(date))
    if orders.empty:
        return []
    return _json_safe(orders.replace({pd.NA: None, float("nan"): None}).to_dict("records"))


# ---------- AI ----------

def get_douyin_ai_config() -> Dict[str, Any]:
    return get_ai_config()


def update_douyin_ai_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return update_ai_config(config)


def test_douyin_ai(config: Dict[str, Any]) -> str:
    return test_ai_connection(config)


def generate_douyin_ai_report(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    analysis = load_douyin_analysis(store_name, start_date, end_date)
    return generate_ai_report(
        kpis=analysis.get("kpis") or {},
        product_metrics=analysis.get("product_metrics") or [],
        config=config,
    )


# ---------- 企业微信 ----------

_DOUYIN_WECOM_CONFIG_FILE = _Path("data/douyin_wecom_config.json")


def _ensure_data_dir():
    _DOUYIN_WECOM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_douyin_wecom_config() -> Dict[str, Any]:
    if not _DOUYIN_WECOM_CONFIG_FILE.exists():
        return {}
    try:
        return _json.loads(_DOUYIN_WECOM_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_douyin_wecom_config(config: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_data_dir()
    _DOUYIN_WECOM_CONFIG_FILE.write_text(_json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def send_douyin_wecom_report(report_date: datetime.date, config: Dict[str, Any]) -> Dict[str, Any]:
    content = build_daily_report(report_date)
    return wecom_sender.send_wecom_report(content=content, config=config)


def get_douyin_records(store_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return _json_safe(list_douyin_records(store_name))


def delete_douyin_record(store_name: str, date: datetime.date) -> Dict[str, Any]:
    date_str = _date_str(date)
    delete_daily_data(store_name, date_str)
    bump_data_version()
    return {"deleted": True, "store_name": store_name, "date": date_str}
