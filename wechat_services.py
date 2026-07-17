"""
微信小店业务服务层
"""

import datetime
import json as _json
from pathlib import Path as _Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from wechat_loader import read_order_file
from wechat_metrics import aggregate_product_metrics, build_product_metrics_from_orders, compute_overall_kpis
from wechat_cost_manager import apply_costs_to_metrics, compute_cost_kpis
from wechat_storage import (
    delete_daily_data,
    list_available_dates,
    list_wechat_records,
    list_wechat_stores,
    load_daily_data,
    load_daily_orders,
    save_daily_data,
)
from services import bump_data_version, cached_with_ttl


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


def _merge_orders(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """按 order_id 合并新旧订单，新数据覆盖旧数据。"""
    if existing.empty or "order_id" not in existing.columns or "order_id" not in new.columns:
        return new.copy()
    existing = existing.copy()
    existing["order_id"] = existing["order_id"].astype(str)
    new = new.copy()
    new["order_id"] = new["order_id"].astype(str)

    existing_indexed = existing.set_index("order_id")
    new_indexed = new.set_index("order_id")
    existing_indexed.update(new_indexed)
    new_only = new_indexed.loc[~new_indexed.index.isin(existing_indexed.index)]
    combined = pd.concat([existing_indexed.reset_index(), new_only.reset_index()], ignore_index=True)
    return combined


def import_wechat_daily_data(
    store_name: str,
    import_date: Optional[datetime.date] = None,
    order_bytes: Optional[bytes] = None,
    order_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """导入微信小店每日订单数据，自动按订单日期拆分保存。"""
    if not order_bytes:
        return {"error": "请上传订单数据"}

    order_df = read_order_file(order_bytes, order_filename or "order.xlsx")
    if order_df.empty:
        return {"store_name": store_name, "date": _date_str(import_date) if import_date else None, "processed_dates": [], "product_rows": 0, "order_rows": 0}

    processed_dates: set = set()
    total_product_rows = 0
    total_order_rows = 0

    order_dates = order_df["order_date"].dropna().unique()
    if import_date and _date_str(import_date) in order_dates:
        order_dates = [_date_str(import_date)]

    for d in order_dates:
        day_orders = order_df[order_df["order_date"] == d].copy()
        if day_orders.empty:
            continue
        existing_product, existing_orders = load_daily_data(store_name, d)
        merged_orders = _merge_orders(existing_orders, day_orders)
        product_metrics = build_product_metrics_from_orders(merged_orders, d)
        meta = {
            "order_file": order_filename or "",
            "product_rows": len(product_metrics),
            "order_rows": len(merged_orders),
            "saved_at": datetime.datetime.now().isoformat(),
        }
        save_daily_data(store_name, d, product_metrics, merged_orders, meta=meta)
        processed_dates.add(d)
        total_product_rows += len(product_metrics)
        total_order_rows += len(merged_orders)

    bump_data_version()

    return {
        "store_name": store_name,
        "date": _date_str(import_date) if import_date else None,
        "processed_dates": sorted(processed_dates),
        "product_rows": total_product_rows,
        "order_rows": total_order_rows,
    }


def _load_wechat_daily_merged(store_name: str, date: str) -> pd.DataFrame:
    """读取当日订单并按最新规则重新汇总商品指标。"""
    _, orders = load_daily_data(store_name, date)
    return build_product_metrics_from_orders(orders, date)


@cached_with_ttl(300)
def load_wechat_analysis(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    product_dfs = [_load_wechat_daily_merged(store_name, d) for d in dates]
    product_dfs = [p for p in product_dfs if not p.empty]

    product_metrics = aggregate_product_metrics(product_dfs)
    product_metrics = apply_costs_to_metrics(product_metrics)
    overall = compute_overall_kpis(product_metrics)
    cost_kpis = compute_cost_kpis(product_metrics)

    return _json_safe({
        "product_metrics": product_metrics.replace({pd.NA: None, float("nan"): None}).to_dict("records"),
        "kpis": overall,
        "cost_kpis": cost_kpis,
    })


@cached_with_ttl(300)
def load_wechat_trend(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> List[Dict[str, Any]]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    dfs: List[pd.DataFrame] = []
    for d in dates:
        p = _load_wechat_daily_merged(store_name, d)
        if not p.empty:
            p = p.copy()
            p["date"] = d
            dfs.append(p)
    if not dfs:
        return []

    combined = pd.concat(dfs, ignore_index=True)
    combined_cost = apply_costs_to_metrics(combined)

    rows = []
    for d, g in combined_cost.groupby("date", sort=True):
        kpis = compute_overall_kpis(g)
        cost = compute_cost_kpis(g)
        rows.append(_json_safe({"date": d, **kpis, **cost}))
    return rows


@cached_with_ttl(300)
def get_wechat_dashboard_summary(
    start_date: datetime.date,
    end_date: datetime.date,
    store_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if store_names is None:
        store_names = list_wechat_stores()

    start_s = _date_str(start_date)
    end_s = _date_str(end_date)

    all_product_dfs: List[pd.DataFrame] = []
    for store in store_names:
        for d in list_available_dates(store):
            if start_s <= d <= end_s:
                p = _load_wechat_daily_merged(store, d)
                if not p.empty:
                    p = p.copy()
                    p["date"] = d
                    all_product_dfs.append(p)

    if not all_product_dfs:
        return _json_safe({
            "store_count": len(store_names),
            "kpis": {},
            "cost_kpis": {},
            "trend": [],
        })

    combined = pd.concat(all_product_dfs, ignore_index=True)
    combined_cost = apply_costs_to_metrics(combined)
    overall = compute_overall_kpis(combined)
    cost_kpis = compute_cost_kpis(combined_cost)

    trend_summary = []
    for d, g in combined_cost.groupby("date", sort=True):
        kpis = compute_overall_kpis(g)
        cost = compute_cost_kpis(g)
        trend_summary.append(_json_safe({"date": d, **kpis, **cost}))

    return _json_safe({
        "store_count": len(store_names),
        "kpis": overall,
        "cost_kpis": cost_kpis,
        "trend": trend_summary,
    })


def get_wechat_orders(store_name: str, date: datetime.date) -> List[Dict[str, Any]]:
    _, orders = load_daily_data(store_name, _date_str(date))
    if orders.empty:
        return []
    return _json_safe(orders.replace({pd.NA: None, float("nan"): None}).to_dict("records"))


def get_wechat_records(store_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return _json_safe(list_wechat_records(store_name))


def delete_wechat_record(store_name: str, date: datetime.date) -> Dict[str, Any]:
    date_str = _date_str(date)
    delete_daily_data(store_name, date_str)
    bump_data_version()
    return {"deleted": True, "store_name": store_name, "date": date_str}


def get_kol_stats(
    store_name: Optional[str],
    start_date: datetime.date,
    end_date: datetime.date,
) -> List[Dict[str, Any]]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    stores = [store_name] if store_name else list_wechat_stores()

    order_dfs: List[pd.DataFrame] = []
    for store in stores:
        for d in list_available_dates(store):
            if start_s <= d <= end_s:
                orders = load_daily_orders(store, d)
                if not orders.empty:
                    order_dfs.append(orders)

    if not order_dfs:
        return []

    df = pd.concat(order_dfs, ignore_index=True)
    df["amount"] = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0)
    df["actual_revenue"] = pd.to_numeric(df.get("actual_revenue", 0), errors="coerce").fillna(0)
    df["refund_amount"] = pd.to_numeric(df.get("refund_amount", 0), errors="coerce").fillna(0)
    df["tech_fee"] = pd.to_numeric(df.get("tech_fee", 0), errors="coerce").fillna(0)
    df["commission"] = pd.to_numeric(df.get("commission", 0), errors="coerce").fillna(0)
    df["net_revenue"] = df["actual_revenue"] - df["refund_amount"] - df["tech_fee"] - df["commission"]
    df["kol_name"] = df.get("kol_name", "").astype(str).str.strip()
    df.loc[df["kol_name"] == "", "kol_name"] = "未知"

    grouped = (
        df.groupby("kol_name")
        .agg(
            kol_id=("kol_id", lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""),
            channel=("channel", lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""),
            order_count=("order_id", "size"),
            gmv=("amount", "sum"),
            net_revenue=("net_revenue", "sum"),
            commission=("commission", "sum"),
            refund_amount=("refund_amount", "sum"),
        )
        .reset_index()
    )
    grouped = grouped.sort_values("gmv", ascending=False)
    return _json_safe(grouped.replace({pd.NA: None, float("nan"): None}).to_dict("records"))


# ---------- 企业微信（占位，与抖音/天猫保持一致） ----------

_WECHAT_WECOM_CONFIG_FILE = _Path("data/wechat_wecom_config.json")


def _ensure_data_dir():
    _WECHAT_WECOM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_wechat_wecom_config() -> Dict[str, Any]:
    if not _WECHAT_WECOM_CONFIG_FILE.exists():
        return {}
    try:
        return _json.loads(_WECHAT_WECOM_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def update_wechat_wecom_config(config: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_data_dir()
    _WECHAT_WECOM_CONFIG_FILE.write_text(_json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config
