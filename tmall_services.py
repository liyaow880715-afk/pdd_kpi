"""
天猫业务服务层
"""

import datetime
import json as _json
from pathlib import Path as _Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from tmall_loader import read_order_file, read_promotion_file
from tmall_metrics import aggregate_product_metrics, build_product_metrics_from_orders, compute_overall_kpis
from tmall_cost_manager import apply_costs_to_metrics, compute_cost_kpis
from tmall_storage import (
    delete_daily_data,
    list_available_dates,
    list_tmall_records,
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


def _build_order_summary(orders_df: pd.DataFrame) -> pd.DataFrame:
    """按商品标题汇总订单数据。"""
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(
            columns=[
                "product_key", "product_name", "order_gmv", "order_actual_revenue",
                "order_count", "valid_order_count", "quantity", "valid_quantity",
                "refund_orders", "refund_amount",
            ]
        )

    df = orders_df.copy()
    df["product_key"] = df["product_name"].astype(str).str.strip()
    df = df[df["product_key"] != ""].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "product_key", "product_name", "order_gmv", "order_actual_revenue",
                "order_count", "valid_order_count", "quantity", "valid_quantity",
                "refund_orders", "refund_amount",
            ]
        )

    df["amount"] = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0)
    df["actual_revenue"] = pd.to_numeric(df.get("actual_revenue", 0), errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0)
    df["refund_amount"] = pd.to_numeric(df.get("refund_amount", 0), errors="coerce").fillna(0)

    df["is_valid"] = True
    df["is_refund"] = df["refund_amount"] > 0
    invalid_status = df["order_status"].astype(str).str.contains("关闭|取消|交易关闭", na=False)
    df.loc[invalid_status, "is_valid"] = False
    df.loc[df["is_refund"], "is_valid"] = False

    grouped = (
        df.groupby("product_key")
        .agg(
            product_name=("product_name", lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""),
            order_gmv=("amount", "sum"),
            order_actual_revenue=("actual_revenue", "sum"),
            order_count=("order_id", "size"),
            quantity=("quantity", "sum"),
            valid_order_gmv=("amount", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            valid_order_count=("order_id", lambda x: x[df.loc[x.index, "is_valid"]].size),
            valid_quantity=("quantity", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            refund_orders=("order_id", lambda x: x[df.loc[x.index, "is_refund"]].size),
            refund_amount=("refund_amount", "sum"),
            merchant_code=("merchant_code", lambda x: _mode_str(x)),
        )
        .reset_index()
    )
    for col in ["valid_order_gmv", "valid_order_count", "valid_quantity", "refund_orders", "refund_amount"]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").fillna(0)
    return grouped


def _mode_str(series: pd.Series) -> str:
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return ""
    return s.mode().iloc[0]


def _merge_order_metrics(product_df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    将订单数据合并到商品指标中。
    天猫推广数据按「计划」维度，订单数据按「商品标题」维度，二者不完全对齐。
    这里按商品标题做外层合并，业务指标以订单为准，推广指标以推广为准。
    """
    order_summary = _build_order_summary(orders_df)

    if product_df is None or product_df.empty:
        if order_summary.empty:
            return pd.DataFrame()
        result = order_summary.rename(columns={
            "product_key": "product_name",
            "order_gmv": "gmv",
            "order_actual_revenue": "actual_revenue",
            "valid_order_gmv": "valid_gmv",
        })
        result["product_id"] = result["product_name"]
        result["spend"] = 0.0
        result["exposure"] = 0.0
        result["clicks"] = 0.0
        return result

    df = product_df.copy()

    if order_summary.empty:
        for col in ["actual_revenue", "quantity", "valid_quantity"]:
            if col not in df.columns:
                df[col] = 0.0
        return df

    order_summary = order_summary.copy()

    for col in ["gmv", "valid_gmv", "order_count", "valid_order_count", "actual_revenue", "quantity", "valid_quantity", "refund_orders", "refund_amount"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    merged = df.merge(order_summary, left_on="product_name", right_on="product_key", how="outer", suffixes=("", "_order"))

    # 合并商品名称：优先使用推广侧（可能为空），否则使用订单侧
    if "product_name_order" in merged.columns:
        merged["product_name"] = merged["product_name"].replace("", pd.NA).fillna(merged["product_name_order"]).fillna("").astype(str)
        merged = merged.drop(columns=["product_name_order"])

    # 合并 plan 相关信息：外层合并后推广侧可能为 NA，需要保留
    merged["product_id"] = merged["product_id"].fillna(merged["product_key"]).fillna(merged["product_name"]).astype(str)
    if "product_key" in merged.columns:
        merged = merged.drop(columns=["product_key"])

    merged["gmv"] = merged.get("order_gmv", 0).fillna(0)
    merged["valid_gmv"] = merged.get("valid_order_gmv", 0).fillna(0)
    merged["order_count"] = merged.get("order_count", 0).fillna(0)
    merged["valid_order_count"] = merged.get("valid_order_count", 0).fillna(0)
    merged["actual_revenue"] = merged.get("order_actual_revenue", 0).fillna(0)
    merged["quantity"] = merged.get("quantity", 0).fillna(0)
    merged["valid_quantity"] = merged.get("valid_quantity", 0).fillna(0)
    refund_orders_col = merged.get("refund_orders", 0)
    refund_amount_col = merged.get("refund_amount", 0)
    merged["refund_orders"] = refund_orders_col.fillna(0) if hasattr(refund_orders_col, "fillna") else float(refund_orders_col)
    merged["refund_amount"] = refund_amount_col.fillna(0) if hasattr(refund_amount_col, "fillna") else float(refund_amount_col)

    for col in ["spend", "exposure", "clicks"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
        else:
            merged[col] = 0.0

    return merged


def _merge_merchant_code_from_orders(product_df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    """兜底：把订单中的商家编码合并到尚未有编码的商品指标。"""
    if product_df is None or product_df.empty:
        return product_df
    df = product_df.copy()
    if "merchant_code" not in df.columns:
        df["merchant_code"] = ""
    if orders_df is None or orders_df.empty or "merchant_code" not in orders_df.columns:
        return df
    needs = df[df["merchant_code"].astype(str).str.strip() == ""]
    if needs.empty:
        return df
    mc = orders_df[orders_df["merchant_code"].astype(str).str.strip() != ""]
    if mc.empty:
        return df
    mode = mc.groupby("product_name")["merchant_code"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "").reset_index()
    mapping = dict(zip(mode["product_name"].astype(str).str.strip(), mode["merchant_code"].astype(str)))
    mask = df["merchant_code"].astype(str).str.strip() == ""
    df.loc[mask, "merchant_code"] = df.loc[mask, "product_name"].astype(str).str.strip().map(mapping).fillna("")
    return df


def import_tmall_daily_data(
    store_name: str,
    import_date: Optional[datetime.date] = None,
    promo_bytes: Optional[bytes] = None,
    promo_filename: Optional[str] = None,
    order_bytes: Optional[bytes] = None,
    order_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """导入天猫每日数据。"""
    processed_dates: set = set()
    total_product_rows = 0
    total_order_rows = 0

    if promo_bytes:
        promo_df = read_promotion_file(promo_bytes, promo_filename or "promo.csv")
        if not promo_df.empty:
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
        order_df = read_order_file(order_bytes, order_filename or "order.xlsx")
        if not order_df.empty:
            order_dates = order_df["order_date"].dropna().unique()
            if import_date and _date_str(import_date) in order_dates:
                order_dates = [_date_str(import_date)]
            for d in order_dates:
                day_orders = order_df[order_df["order_date"] == d]
                if day_orders.empty:
                    continue
                existing_product = load_daily_data(store_name, d)[0]
                existing_product = _merge_order_metrics(existing_product, day_orders)
                existing_product["date"] = d
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


def load_tmall_analysis(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    product_dfs = []
    for d in dates:
        p, o = load_daily_data(store_name, d)
        p = _merge_order_metrics(p, o)
        p = _merge_merchant_code_from_orders(p, o)
        if not p.empty:
            product_dfs.append(p)

    product_metrics = aggregate_product_metrics(product_dfs)
    product_metrics = apply_costs_to_metrics(product_metrics, store_name=store_name)
    overall = compute_overall_kpis(product_metrics)
    cost_kpis = compute_cost_kpis(product_metrics)

    return _json_safe({
        "product_metrics": product_metrics.replace({pd.NA: None, float("nan"): None}).to_dict("records"),
        "kpis": overall,
        "cost_kpis": cost_kpis,
    })


def load_tmall_trend(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> List[Dict[str, Any]]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    dates = [d for d in list_available_dates(store_name) if start_s <= d <= end_s]

    rows = []
    for d in dates:
        p, o = load_daily_data(store_name, d)
        p = _merge_order_metrics(p, o)
        p = _merge_merchant_code_from_orders(p, o)
        p_cost = apply_costs_to_metrics(p, store_name=store_name)
        kpis = compute_overall_kpis(p)
        cost = compute_cost_kpis(p_cost)
        row = {"date": d, **kpis, **cost}
        rows.append(_json_safe(row))
    return rows


def get_tmall_dashboard_summary(
    start_date: datetime.date,
    end_date: datetime.date,
    store_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from tmall_storage import list_tmall_stores

    if store_names is None:
        store_names = list_tmall_stores()

    start_s = _date_str(start_date)
    end_s = _date_str(end_date)

    all_product_dfs: List[pd.DataFrame] = []
    daily_dfs: Dict[str, List[pd.DataFrame]] = {}
    for store in store_names:
        for d in list_available_dates(store):
            if start_s <= d <= end_s:
                p, o = load_daily_data(store, d)
                p = _merge_order_metrics(p, o)
                p = _merge_merchant_code_from_orders(p, o)
                if not p.empty:
                    all_product_dfs.append(p)
                    daily_dfs.setdefault(d, []).append(p)

    combined = pd.concat(all_product_dfs, ignore_index=True) if all_product_dfs else pd.DataFrame()
    combined_cost = apply_costs_to_metrics(combined, store_name=None)
    overall = compute_overall_kpis(combined)
    cost_kpis = compute_cost_kpis(combined_cost)

    trend_summary = []
    for d in sorted(daily_dfs.keys()):
        day_df = pd.concat(daily_dfs[d], ignore_index=True)
        day_cost = apply_costs_to_metrics(day_df, store_name=None)
        kpis = compute_overall_kpis(day_df)
        cost = compute_cost_kpis(day_cost)
        trend_summary.append(_json_safe({"date": d, **kpis, **cost}))

    return _json_safe({
        "store_count": len(store_names),
        "kpis": overall,
        "cost_kpis": cost_kpis,
        "trend": trend_summary,
    })


def get_tmall_orders(store_name: str, date: datetime.date) -> List[Dict[str, Any]]:
    _, orders = load_daily_data(store_name, _date_str(date))
    if orders.empty:
        return []
    return _json_safe(orders.replace({pd.NA: None, float("nan"): None}).to_dict("records"))


def get_tmall_records(store_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return _json_safe(list_tmall_records(store_name))


def delete_tmall_record(store_name: str, date: datetime.date) -> Dict[str, Any]:
    date_str = _date_str(date)
    delete_daily_data(store_name, date_str)
    bump_data_version()
    return {"deleted": True, "store_name": store_name, "date": date_str}
