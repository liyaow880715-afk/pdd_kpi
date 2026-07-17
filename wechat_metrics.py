"""
微信小店指标计算
"""

from typing import Any, Dict, List

import pandas as pd


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def compute_overall_kpis(metrics: pd.DataFrame) -> Dict[str, Any]:
    if metrics is None or metrics.empty:
        return {}

    totals = {
        "gmv": float(metrics["gmv"].sum()),
        "actual_revenue": float(metrics["actual_revenue"].sum()),
        "valid_gmv": float(metrics.get("valid_gmv", pd.Series([0.0])).sum()),
        "order_count": float(metrics["order_count"].sum()),
        "valid_order_count": float(metrics.get("valid_order_count", pd.Series([0.0])).sum()),
        "quantity": float(metrics.get("quantity", pd.Series([0.0])).sum()),
        "valid_quantity": float(metrics.get("valid_quantity", pd.Series([0.0])).sum()),
        "refund_amount": float(metrics.get("refund_amount", pd.Series([0.0])).sum()),
        "refund_orders": float(metrics.get("refund_orders", pd.Series([0.0])).sum()),
        "tech_fee": float(metrics.get("tech_fee", pd.Series([0.0])).sum()),
        "commission": float(metrics.get("commission", pd.Series([0.0])).sum()),
        "net_revenue": float(metrics.get("net_revenue", pd.Series([0.0])).sum()),
    }

    totals["refund_rate"] = safe_div(totals["refund_orders"], totals["order_count"]) * 100
    totals["refund_amount_rate"] = safe_div(totals["refund_amount"], totals["gmv"]) * 100
    totals["commission_rate"] = safe_div(totals["commission"], totals["actual_revenue"]) * 100

    return totals


def _first_non_empty(series: pd.Series) -> str:
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    return s.iloc[0] if len(s) else ""


def build_product_metrics_from_orders(orders: pd.DataFrame, date: str) -> pd.DataFrame:
    """从订单数据汇总商品维度指标。"""
    if orders is None or orders.empty:
        return pd.DataFrame()

    df = orders.copy()
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df = df[df["product_id"] != ""].copy()
    if df.empty:
        return pd.DataFrame()

    df["amount"] = pd.to_numeric(df.get("amount", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["actual_revenue"] = pd.to_numeric(df.get("actual_revenue", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df.get("quantity", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["refund_amount"] = pd.to_numeric(df.get("refund_amount", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["tech_fee"] = pd.to_numeric(df.get("tech_fee", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["commission"] = pd.to_numeric(df.get("commission", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["net_revenue"] = pd.to_numeric(df.get("net_revenue", pd.Series(0, index=df.index)), errors="coerce").fillna(0)

    if "is_valid" not in df.columns:
        invalid_status = df["order_status"].astype(str).str.contains("取消|关闭", na=False)
        df["is_valid"] = (df["actual_revenue"] > 0) & (~invalid_status)
    df["is_refund"] = df["refund_amount"] > 0

    grouped = (
        df.groupby("product_id")
        .agg(
            product_name=("product_name", lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""),
            sku_code=("sku_code", _first_non_empty),
            platform_sku_code=("platform_sku_code", _first_non_empty),
            gmv=("amount", "sum"),
            actual_revenue=("actual_revenue", "sum"),
            order_count=("order_id", "size"),
            quantity=("quantity", "sum"),
            valid_gmv=("net_revenue", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            valid_order_count=("order_id", lambda x: x[df.loc[x.index, "is_valid"]].size),
            valid_quantity=("quantity", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            refund_orders=("order_id", lambda x: x[df.loc[x.index, "is_refund"]].size),
            refund_amount=("refund_amount", "sum"),
            tech_fee=("tech_fee", "sum"),
            commission=("commission", "sum"),
            net_revenue=("net_revenue", "sum"),
        )
        .reset_index()
    )

    grouped["date"] = date
    return grouped[[
        "product_id", "product_name", "sku_code", "platform_sku_code", "date",
        "gmv", "actual_revenue", "order_count", "quantity",
        "valid_gmv", "valid_order_count", "valid_quantity",
        "refund_orders", "refund_amount", "tech_fee", "commission", "net_revenue",
    ]]


def aggregate_product_metrics(daily_list: List[pd.DataFrame]) -> pd.DataFrame:
    """按 product_id 汇总多日商品指标。"""
    if not daily_list:
        return pd.DataFrame()
    combined = pd.concat(daily_list, ignore_index=True)
    if combined.empty:
        return combined

    sum_cols = [
        "gmv", "actual_revenue", "order_count", "quantity",
        "valid_gmv", "valid_order_count", "valid_quantity",
        "refund_orders", "refund_amount", "tech_fee", "commission", "net_revenue",
    ]
    agg = {c: "sum" for c in sum_cols if c in combined.columns}
    agg["product_name"] = lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""
    if "sku_code" in combined.columns:
        agg["sku_code"] = _first_non_empty
    if "platform_sku_code" in combined.columns:
        agg["platform_sku_code"] = _first_non_empty

    grouped = combined.groupby("product_id").agg(agg).reset_index()
    grouped["refund_rate"] = grouped.apply(lambda r: safe_div(r["refund_orders"], r["order_count"]) * 100, axis=1)
    grouped["refund_amount_rate"] = grouped.apply(lambda r: safe_div(r["refund_amount"], r["gmv"]) * 100, axis=1)
    return grouped
