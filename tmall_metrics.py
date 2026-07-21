"""
天猫指标计算
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
        "direct_gmv": float(metrics.get("direct_gmv", pd.Series([0.0])).sum()),
        "indirect_gmv": float(metrics.get("indirect_gmv", pd.Series([0.0])).sum()),
        "cart_count": float(metrics.get("cart_count", pd.Series([0.0])).sum()),
        "collect_count": float(metrics.get("collect_count", pd.Series([0.0])).sum()),
    }
    if "actual_revenue" in metrics.columns:
        totals["actual_revenue"] = float(metrics["actual_revenue"].sum())
    if "quantity" in metrics.columns:
        totals["quantity"] = float(metrics["quantity"].sum())
    if "valid_quantity" in metrics.columns:
        totals["valid_quantity"] = float(metrics["valid_quantity"].sum())

    for col in ["promo_gmv", "promo_valid_gmv", "promo_order_count", "promo_valid_order_count",
                "new_buyer_count", "natural_gmv", "platform_subsidy", "subsidy_gmv"]:
        if col in metrics.columns:
            totals[col] = float(metrics[col].sum())

    totals["roi"] = safe_div(totals["gmv"], totals["spend"])
    totals["valid_roi"] = safe_div(totals["valid_gmv"], totals["spend"])
    if "promo_gmv" in totals:
        totals["promo_roi"] = safe_div(totals["promo_gmv"], totals["spend"])
    # 投流费比 = 消耗 / 净成交金额
    totals["promo_cost_ratio"] = safe_div(totals["spend"], totals["valid_gmv"]) * 100
    totals["ctr"] = safe_div(totals["clicks"], totals["exposure"]) * 100
    totals["cvr"] = safe_div(totals["order_count"], totals["clicks"]) * 100
    totals["cpc"] = safe_div(totals["spend"], totals["clicks"])
    totals["cpm"] = safe_div(totals["spend"], totals["exposure"]) * 1000
    totals["refund_rate"] = safe_div(totals["refund_orders"], totals["order_count"]) * 100
    totals["refund_amount_rate"] = safe_div(totals["refund_amount"], totals["gmv"]) * 100

    return totals


def build_product_metrics_from_orders(orders: pd.DataFrame, date: str) -> pd.DataFrame:
    """当某天没有推广数据时，从订单数据反推基础商品指标（消耗/曝光/点击为 0）。"""
    if orders is None or orders.empty:
        return pd.DataFrame()

    df = orders.copy().reset_index(drop=True)
    df["product_key"] = df["product_name"].astype(str).str.strip()
    df["amount"] = pd.to_numeric(df.get("amount", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["actual_revenue"] = pd.to_numeric(df.get("actual_revenue", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df.get("quantity", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["refund_amount"] = pd.to_numeric(df.get("refund_amount", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
    df["compensation_amount"] = pd.to_numeric(df.get("compensation_amount", pd.Series(0, index=df.index)), errors="coerce").fillna(0)

    # 净订单：买家有实际付款且订单未关闭/取消
    invalid_status = df["order_status"].astype(str).str.contains("关闭|取消|交易关闭|待付款|未付款", na=False)
    df["is_valid"] = (df["actual_revenue"] > 0) & (~invalid_status)
    df["is_refund"] = df["refund_amount"] > 0
    df["net_revenue"] = df["actual_revenue"] - df["refund_amount"] - df["compensation_amount"]

    grouped = (
        df.groupby("product_key")
        .agg(
            product_name=("product_name", lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""),
            gmv=("amount", "sum"),
            actual_revenue=("actual_revenue", "sum"),
            order_count=("order_id", "size"),
            quantity=("quantity", "sum"),
            valid_gmv=("net_revenue", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            valid_order_count=("order_id", lambda x: x[df.loc[x.index, "is_valid"]].size),
            valid_quantity=("quantity", lambda x: x[df.loc[x.index, "is_valid"]].sum()),
            refund_orders=("order_id", lambda x: x[df.loc[x.index, "is_refund"]].size),
            refund_amount=("refund_amount", "sum"),
        )
        .reset_index()
    )

    grouped["date"] = date
    grouped["spend"] = 0.0
    grouped["exposure"] = 0.0
    grouped["clicks"] = 0.0
    grouped["product_id"] = grouped["product_key"]

    return grouped[[
        "product_id", "product_name", "product_key", "date",
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "exposure", "clicks", "refund_orders", "refund_amount", "actual_revenue",
        "quantity", "valid_quantity",
    ]]


def aggregate_product_metrics(daily_list: List[pd.DataFrame]) -> pd.DataFrame:
    """按 product_id 汇总多日商品指标"""
    if not daily_list:
        return pd.DataFrame()
    combined = pd.concat(daily_list, ignore_index=True)
    if combined.empty:
        return combined

    sum_cols = [
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "exposure", "clicks", "refund_orders", "refund_amount", "actual_revenue",
        "quantity", "valid_quantity",
        "direct_gmv", "indirect_gmv", "direct_order_count", "indirect_order_count",
        "cart_count", "collect_count", "presell_gmv", "presell_order_count",
        "promo_gmv", "promo_valid_gmv", "promo_order_count", "promo_valid_order_count",
        "new_buyer_count", "natural_gmv", "platform_subsidy", "subsidy_gmv",
    ]
    agg = {c: "sum" for c in sum_cols if c in combined.columns}

    def _join_ids(x):
        ids = set()
        for v in x.dropna().astype(str):
            ids.update(p for p in (s.strip() for s in v.split(",")) if p and p != "nan")
        return ",".join(sorted(ids))

    agg["product_name"] = lambda x: x.dropna().astype(str).iloc[0] if len(x) else ""
    if "merchant_code" in combined.columns:
        def _first_non_empty_code(x):
            codes = x.dropna().astype(str).str.strip()
            codes = codes[codes != ""]
            return codes.iloc[0] if len(codes) else ""
        agg["merchant_code"] = _first_non_empty_code

    # 按 product_id 聚合：商品标题可能中途改名（如同一链接加【顺丰冷链】前缀），
    # ID 更稳定；同标题多主体ID 的订单重复计数已在日级合并时按标题聚合解决
    grouped = combined.groupby("product_id", dropna=False).agg(agg).reset_index()
    grouped["roi"] = grouped.apply(lambda r: safe_div(r["gmv"], r["spend"]), axis=1)
    grouped["valid_roi"] = grouped.apply(lambda r: safe_div(r["valid_gmv"], r["spend"]), axis=1)
    if "promo_gmv" in grouped.columns:
        grouped["promo_roi"] = grouped.apply(lambda r: safe_div(r["promo_gmv"], r["spend"]), axis=1)
    # 投流费比 = 消耗 / 净成交金额
    grouped["promo_cost_ratio"] = grouped.apply(lambda r: safe_div(r["spend"], r["valid_gmv"]) * 100, axis=1)
    grouped["ctr"] = grouped.apply(lambda r: safe_div(r["clicks"], r["exposure"]) * 100, axis=1)
    grouped["cvr"] = grouped.apply(lambda r: safe_div(r["order_count"], r["clicks"]) * 100, axis=1)
    grouped["refund_rate"] = grouped.apply(lambda r: safe_div(r["refund_orders"], r["order_count"]) * 100, axis=1)
    return grouped
