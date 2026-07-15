"""
抖音指标计算
"""

from typing import Any, Dict, List

import pandas as pd


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def compute_overall_kpis(metrics: pd.DataFrame) -> Dict[str, Any]:
    if metrics is None or metrics.empty:
        return {}

    totals = {
        "spend": float(metrics["spend"].sum()),
        "gmv": float(metrics["gmv"].sum()),
        "valid_gmv": float(metrics["valid_gmv"].sum()),
        "order_count": float(metrics["order_count"].sum()),
        "valid_order_count": float(metrics["valid_order_count"].sum()),
        "exposure": float(metrics["exposure"].sum()),
        "clicks": float(metrics["clicks"].sum()),
        "refund_orders": float(metrics["refund_orders"].sum()),
        "refund_amount": float(metrics["refund_amount"].sum()),
    }

    totals["roi"] = safe_div(totals["gmv"], totals["spend"])
    totals["valid_roi"] = safe_div(totals["valid_gmv"], totals["spend"])
    totals["ctr"] = safe_div(totals["clicks"], totals["exposure"]) * 100
    totals["cvr"] = safe_div(totals["order_count"], totals["clicks"]) * 100
    totals["cpc"] = safe_div(totals["spend"], totals["clicks"])
    totals["cpm"] = safe_div(totals["spend"], totals["exposure"]) * 1000
    totals["refund_rate"] = safe_div(totals["refund_orders"], totals["order_count"]) * 100
    totals["refund_amount_rate"] = safe_div(totals["refund_amount"], totals["gmv"]) * 100

    return totals


def aggregate_product_metrics(daily_list: List[pd.DataFrame]) -> pd.DataFrame:
    """按 product_id 汇总多日商品指标"""
    if not daily_list:
        return pd.DataFrame()
    combined = pd.concat(daily_list, ignore_index=True)
    if combined.empty:
        return combined

    sum_cols = [
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "exposure", "clicks", "refund_orders", "refund_amount",
    ]
    agg = {c: "sum" for c in sum_cols if c in combined.columns}
    agg["product_name"] = lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""

    grouped = combined.groupby("product_id").agg(agg).reset_index()
    grouped["roi"] = grouped.apply(lambda r: safe_div(r["gmv"], r["spend"]), axis=1)
    grouped["valid_roi"] = grouped.apply(lambda r: safe_div(r["valid_gmv"], r["spend"]), axis=1)
    grouped["ctr"] = grouped.apply(lambda r: safe_div(r["clicks"], r["exposure"]) * 100, axis=1)
    grouped["cvr"] = grouped.apply(lambda r: safe_div(r["order_count"], r["clicks"]) * 100, axis=1)
    grouped["refund_rate"] = grouped.apply(lambda r: safe_div(r["refund_orders"], r["order_count"]) * 100, axis=1)
    return grouped
