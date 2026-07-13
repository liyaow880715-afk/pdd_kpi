"""
指标计算模块：从匹配后的宽表计算 KPI
"""

import pandas as pd
import numpy as np
from typing import Dict, List


def safe_div(numerator, denominator, default=0.0):
    """安全除法，避免除以 0"""
    if denominator == 0 or pd.isna(denominator):
        return default
    return numerator / denominator


def compute_product_metrics(merged: pd.DataFrame) -> pd.DataFrame:
    """
    在匹配后的 DataFrame 上计算商品/样式级指标
    """
    df = merged.copy()

    # 填充空值
    numeric_cols = [
        "promo_spend", "promo_gmv", "promo_orders",
        "exposure", "clicks",
        "order_count", "valid_order_count", "order_gmv", "valid_order_gmv",
        "merchant_income", "valid_merchant_income",
        "refund_count", "cancel_count", "quantity", "valid_quantity"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 推广侧指标
    df["promo_roi"] = df.apply(
        lambda r: safe_div(r["promo_gmv"], r["promo_spend"]), axis=1
    )
    df["promo_cost_per_order"] = df.apply(
        lambda r: safe_div(r["promo_spend"], r["promo_orders"]), axis=1
    )
    df["ctr"] = df.apply(
        lambda r: safe_div(r["clicks"], r["exposure"]) * 100, axis=1
    )
    df["click_to_order_rate"] = df.apply(
        lambda r: safe_div(r["promo_orders"], r["clicks"]) * 100, axis=1
    )
    df["cpc"] = df.apply(
        lambda r: safe_div(r["promo_spend"], r["clicks"]), axis=1
    )

    # 订单侧指标（全部订单）
    df["refund_rate"] = df.apply(
        lambda r: safe_div(r["refund_count"], r["order_count"]) * 100, axis=1
    )
    df["cancel_rate"] = df.apply(
        lambda r: safe_div(r["cancel_count"], r["order_count"]) * 100, axis=1
    )
    df["problem_rate"] = df.apply(
        lambda r: safe_div(r["refund_count"] + r["cancel_count"], r["order_count"]) * 100,
        axis=1,
    )

    # 真实 ROI：剔除退款和取消订单后的商家实收 / 推广花费
    df["real_roi_merchant_income"] = df.apply(
        lambda r: safe_div(r["valid_merchant_income"], r["promo_spend"]), axis=1
    )
    df["valid_order_gmv_roi"] = df.apply(
        lambda r: safe_div(r["valid_order_gmv"], r["promo_spend"]), axis=1
    )

    # 自然流量估算（基于全部订单）
    df["organic_orders"] = (df["order_count"] - df["promo_orders"]).clip(lower=0)
    df["organic_gmv"] = (df["order_gmv"] - df["promo_gmv"]).clip(lower=0)
    df["organic_ratio_gmv"] = df.apply(
        lambda r: safe_div(r["organic_gmv"], r["order_gmv"]) * 100, axis=1
    )
    df["organic_ratio_orders"] = df.apply(
        lambda r: safe_div(r["organic_orders"], r["order_count"]) * 100, axis=1
    )

    # 实收拆分估算：按 GMV 比例拆分有效商家实收
    df["promo_merchant_income"] = df.apply(
        lambda r: r["promo_gmv"] * safe_div(r["valid_merchant_income"], r["order_gmv"]), axis=1
    )
    df["organic_merchant_income"] = (df["valid_merchant_income"] - df["promo_merchant_income"]).clip(lower=0)
    df["organic_ratio_income"] = df.apply(
        lambda r: safe_div(r["organic_merchant_income"], r["valid_merchant_income"]) * 100, axis=1
    )

    # 每单贡献
    df["avg_order_gmv"] = df.apply(
        lambda r: safe_div(r["order_gmv"], r["order_count"]), axis=1
    )
    df["avg_valid_order_gmv"] = df.apply(
        lambda r: safe_div(r["valid_order_gmv"], r["valid_order_count"]), axis=1
    )
    df["avg_order_income"] = df.apply(
        lambda r: safe_div(r["merchant_income"], r["order_count"]), axis=1
    )
    df["avg_valid_order_income"] = df.apply(
        lambda r: safe_div(r["valid_merchant_income"], r["valid_order_count"]), axis=1
    )

    return df


def compute_overall_kpis(metrics: pd.DataFrame) -> Dict[str, float]:
    """计算整体 KPI"""
    # 成本相关字段（如果已应用）
    cost_totals = {}
    if metrics is not None and not metrics.empty:
        for col in ["total_cost", "link_gross_profit", "profit_loss"]:
            if col in metrics.columns:
                cost_totals[col] = pd.to_numeric(metrics[col], errors="coerce").fillna(0).sum()
        if "valid_merchant_income" in metrics.columns and cost_totals.get("link_gross_profit") is not None:
            income = pd.to_numeric(metrics["valid_merchant_income"], errors="coerce").fillna(0).sum()
            cost_totals["gross_margin_rate"] = (cost_totals["link_gross_profit"] / income * 100) if income else 0.0

    totals = {
        "promo_spend": metrics["promo_spend"].sum(),
        "promo_gmv": metrics["promo_gmv"].sum(),
        "promo_orders": metrics["promo_orders"].sum(),
        "exposure": metrics["exposure"].sum(),
        "clicks": metrics["clicks"].sum(),
        "order_count": metrics["order_count"].sum(),
        "valid_order_count": metrics["valid_order_count"].sum(),
        "order_gmv": metrics["order_gmv"].sum(),
        "valid_order_gmv": metrics["valid_order_gmv"].sum(),
        "merchant_income": metrics["merchant_income"].sum(),
        "valid_merchant_income": metrics["valid_merchant_income"].sum(),
        "refund_count": metrics["refund_count"].sum(),
        "cancel_count": metrics["cancel_count"].sum(),
        "organic_orders": metrics["organic_orders"].sum(),
        "organic_gmv": metrics["organic_gmv"].sum(),
    }

    kpis = {
        "promo_spend": totals["promo_spend"],
        "promo_gmv": totals["promo_gmv"],
        "order_gmv": totals["order_gmv"],
        "valid_order_gmv": totals["valid_order_gmv"],
        "merchant_income": totals["merchant_income"],
        "valid_merchant_income": totals["valid_merchant_income"],
        "promo_roi": safe_div(totals["promo_gmv"], totals["promo_spend"]),
        "real_roi": safe_div(totals["valid_merchant_income"], totals["promo_spend"]),
        "valid_order_gmv_roi": safe_div(totals["valid_order_gmv"], totals["promo_spend"]),
        "refund_rate": safe_div(totals["refund_count"], totals["order_count"]) * 100,
        "cancel_rate": safe_div(totals["cancel_count"], totals["order_count"]) * 100,
        "problem_rate": safe_div(
            totals["refund_count"] + totals["cancel_count"], totals["order_count"]
        ) * 100,
        "ctr": safe_div(totals["clicks"], totals["exposure"]) * 100,
        "click_to_order_rate": safe_div(totals["promo_orders"], totals["clicks"]) * 100,
        "cpc": safe_div(totals["promo_spend"], totals["clicks"]),
        "organic_ratio_gmv": safe_div(totals["organic_gmv"], totals["order_gmv"]) * 100,
        "organic_ratio_orders": safe_div(totals["organic_orders"], totals["order_count"]) * 100,
        "order_count": totals["order_count"],
        "valid_order_count": totals["valid_order_count"],
        "promo_orders": totals["promo_orders"],
        "organic_orders": totals["organic_orders"],
        "organic_gmv": totals["organic_gmv"],
        "refund_count": totals["refund_count"],
        "cancel_count": totals["cancel_count"],
        **cost_totals,
    }
    return kpis


def aggregate_product_metrics(daily_metrics_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    将多日的商品级指标按商品汇总，并重新计算衍生比率
    """
    if not daily_metrics_list:
        return pd.DataFrame()

    # 合并所有日期
    combined = pd.concat(daily_metrics_list, ignore_index=True)
    if combined.empty:
        return combined

    # 分组键：优先用 product_id，否则 product_name
    group_cols = ["product_name"]
    if "product_id" in combined.columns and combined["product_id"].notna().any():
        group_cols = ["product_id", "product_name"]

    # 需要求和的字段
    sum_cols = [
        "promo_spend", "promo_gmv", "promo_orders",
        "exposure", "clicks",
        "order_count", "valid_order_count", "order_gmv", "valid_order_gmv",
        "merchant_income", "valid_merchant_income",
        "refund_count", "cancel_count", "quantity", "valid_quantity",
        "organic_orders", "organic_gmv",
    ]
    sum_cols = [c for c in sum_cols if c in combined.columns]

    agg = combined.groupby(group_cols, as_index=False)[sum_cols].sum()

    # 保留 product_name 作为唯一分组键传给 compute_product_metrics
    if "product_id" in agg.columns:
        agg = agg.drop(columns=["product_id"])

    return compute_product_metrics(agg)


def aggregate_overall_kpis(daily_metrics_list: List[pd.DataFrame]) -> Dict[str, float]:
    """汇总多日的整体 KPI"""
    metrics = aggregate_product_metrics(daily_metrics_list)
    if metrics.empty:
        return {}
    return compute_overall_kpis(metrics)


def aggregate_style_metrics(daily_orders_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    将多日的订单明细合并后重新计算样式级指标
    """
    if not daily_orders_list:
        return pd.DataFrame()
    combined = pd.concat(daily_orders_list, ignore_index=True)
    if combined.empty:
        return combined
    return compute_style_metrics(combined)


def compute_style_metrics(orders: pd.DataFrame) -> pd.DataFrame:
    """
    按样式/规格汇总订单数据（用于样式分析页）
    """
    group_cols = ["product_id", "product_name"]
    if "style_id" in orders.columns and orders["style_id"].notna().any():
        group_cols.append("style_id")
    if "style_name" in orders.columns and orders["style_name"].notna().any():
        group_cols.append("style_name")

    agg = orders.groupby(group_cols, as_index=False).agg(
        order_count=("order_id", "count"),
        valid_order_count=("is_valid", "sum"),
        quantity=("quantity", "sum"),
        valid_quantity=("is_valid", lambda x: (orders.loc[x.index, "quantity"] * x).sum()),
        order_gmv=("item_total", "sum"),
        valid_order_gmv=("is_valid", lambda x: (orders.loc[x.index, "item_total"] * x).sum()),
        user_paid=("user_paid", "sum"),
        valid_user_paid=("is_valid", lambda x: (orders.loc[x.index, "user_paid"] * x).sum()),
        merchant_income=("merchant_income", "sum"),
        valid_merchant_income=("is_valid", lambda x: (orders.loc[x.index, "merchant_income"] * x).sum()),
        refund_count=("is_refund", "sum"),
        cancel_count=("is_cancel", "sum"),
    )

    agg["refund_rate"] = agg.apply(
        lambda r: safe_div(r["refund_count"], r["order_count"]) * 100, axis=1
    )
    agg["cancel_rate"] = agg.apply(
        lambda r: safe_div(r["cancel_count"], r["order_count"]) * 100, axis=1
    )
    agg["avg_order_gmv"] = agg.apply(
        lambda r: safe_div(r["order_gmv"], r["order_count"]), axis=1
    )
    agg["avg_valid_order_gmv"] = agg.apply(
        lambda r: safe_div(r["valid_order_gmv"], r["valid_order_count"]), axis=1
    )
    agg["avg_order_income"] = agg.apply(
        lambda r: safe_div(r["merchant_income"], r["order_count"]), axis=1
    )
    agg["avg_valid_order_income"] = agg.apply(
        lambda r: safe_div(r["valid_merchant_income"], r["valid_order_count"]), axis=1
    )
    return agg
