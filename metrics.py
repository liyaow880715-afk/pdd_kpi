"""
指标计算模块：从匹配后的宽表计算 KPI
"""

import pandas as pd
import numpy as np
from typing import Dict, List


# 平台技术服务费费率：按商家实收的 0.6% 从有效商家实收中扣除
PLATFORM_FEE_RATE = 0.006


def safe_div(numerator, denominator, default=0.0):
    """安全除法，避免除以 0"""
    if denominator == 0 or pd.isna(denominator):
        return default
    return numerator / denominator


def _aggregate_refund_stage_counts_from_orders(order_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """从订单明细中按 product_id 汇总未发货/已发货/已收货退款数（兼容旧数据）"""
    from data_processor import _classify_refund_stage
    if not order_dfs:
        return pd.DataFrame(columns=["product_id", "refund_unshipped_count", "refund_shipped_count", "refund_received_count"])
    combined = pd.concat(order_dfs, ignore_index=True)
    if combined.empty or "product_id" not in combined.columns:
        return pd.DataFrame(columns=["product_id", "refund_unshipped_count", "refund_shipped_count", "refund_received_count"])

    # 退款标记兼容旧数据
    if "is_refund" not in combined.columns:
        status = combined.get("order_status", "")
        aftersales = combined.get("aftersales_status", "")
        combined["is_refund"] = (
            status.astype(str).str.contains("退款成功") |
            aftersales.astype(str).str.contains("退款成功") |
            status.astype(str).str.contains("售后中")
        ).astype(int)

    combined = combined.copy()
    combined["refund_stage"] = combined.apply(
        lambda r: _classify_refund_stage(r) if r.get("is_refund") == 1 else "", axis=1
    )
    for stage, col in [("unshipped", "is_refund_unshipped"), ("shipped", "is_refund_shipped"), ("received", "is_refund_received")]:
        combined[col] = (combined["refund_stage"] == stage).astype(int)

    agg = combined.groupby("product_id", as_index=False).agg(
        refund_unshipped_count=("is_refund_unshipped", "sum"),
        refund_shipped_count=("is_refund_shipped", "sum"),
        refund_received_count=("is_refund_received", "sum"),
    )
    return agg


def merge_refund_stage_counts(metrics: pd.DataFrame, order_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """若商品指标缺少退款阶段字段，或阶段字段与总退款数不匹配，则从订单明细补齐"""
    if metrics is None or metrics.empty:
        return metrics
    stage_cols = ["refund_unshipped_count", "refund_shipped_count", "refund_received_count"]
    stage_present = all(c in metrics.columns for c in stage_cols)
    if stage_present:
        stage_sum = metrics[stage_cols].sum().sum()
        refund_total = metrics.get("refund_count", pd.Series(0, index=metrics.index)).sum()
        if abs(stage_sum - refund_total) < 1e-6:
            return metrics
    if not order_dfs:
        return metrics
    agg = _aggregate_refund_stage_counts_from_orders(order_dfs)
    if agg.empty:
        return metrics
    # 避免旧数据的 0 字段与 agg 字段重名导致合并后产生 _x/_y
    metrics = metrics.drop(columns=[c for c in stage_cols if c in metrics.columns])
    metrics = metrics.merge(agg, on="product_id", how="left")
    for c in stage_cols:
        if c in metrics.columns:
            metrics[c] = metrics[c].fillna(0)
    return metrics


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
        "refund_count", "cancel_count",
        "refund_unshipped_count", "refund_shipped_count", "refund_received_count",
        "quantity", "valid_quantity"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 兼容旧数据：退款阶段字段不存在时补 0
    for c in ["refund_unshipped_count", "refund_shipped_count", "refund_received_count"]:
        if c not in df.columns:
            df[c] = 0

    # 平台技术服务费 = 有效商家实收 * 0.6%（剔除退款/取消/待付款订单）
    # 单独展示，不扣减有效商家实收；在毛利中扣除
    if "valid_merchant_income" in df.columns:
        df["platform_fee"] = df["valid_merchant_income"] * PLATFORM_FEE_RATE

    # 预计算衍生列一律作废，统一重算（保证口径与代码一致）
    _precomputed_cols = [
        "promo_roi", "promo_cost_per_order", "ctr", "click_to_order_rate",
        "exposure_to_order_rate", "cpc", "cpm", "promo_gmv_ratio",
        "valid_order_gmv_ratio", "promo_order_ratio", "refund_rate",
        "cancel_rate", "problem_rate", "refund_unshipped_rate",
        "refund_shipped_rate", "refund_received_rate", "real_roi_merchant_income",
        "valid_order_gmv_roi", "promo_cost_ratio", "organic_orders",
        "organic_gmv", "organic_ratio_gmv", "organic_ratio_orders",
        "promo_merchant_income", "organic_merchant_income", "organic_ratio_income",
        "promo_valid_order_count", "organic_valid_order_count",
        "organic_ratio_valid_orders", "avg_order_gmv", "avg_valid_order_gmv",
        "avg_order_income", "avg_valid_order_income",
    ]
    df = df.drop(columns=[c for c in _precomputed_cols if c in df.columns])

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
    df["exposure_to_order_rate"] = df.apply(
        lambda r: safe_div(r["promo_orders"], r["exposure"]) * 100, axis=1
    )
    df["cpc"] = df.apply(
        lambda r: safe_div(r["promo_spend"], r["clicks"]), axis=1
    )
    df["cpm"] = df.apply(
        lambda r: safe_div(r["promo_spend"], r["exposure"]) * 1000, axis=1
    )
    df["promo_gmv_ratio"] = df.apply(
        lambda r: safe_div(r["promo_gmv"], r["order_gmv"]) * 100, axis=1
    )
    df["valid_order_gmv_ratio"] = df.apply(
        lambda r: safe_div(r["valid_order_gmv"], r["order_gmv"]) * 100, axis=1
    )
    df["promo_order_ratio"] = df.apply(
        lambda r: safe_div(r["promo_orders"], r["order_count"]) * 100, axis=1
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
    df["refund_unshipped_rate"] = df.apply(
        lambda r: safe_div(r["refund_unshipped_count"], r["order_count"]) * 100, axis=1
    )
    df["refund_shipped_rate"] = df.apply(
        lambda r: safe_div(r["refund_shipped_count"], r["order_count"]) * 100, axis=1
    )
    df["refund_received_rate"] = df.apply(
        lambda r: safe_div(r["refund_received_count"], r["order_count"]) * 100, axis=1
    )

    # 真实 ROI：剔除退款和取消订单后的商家实收 / 推广花费
    df["real_roi_merchant_income"] = df.apply(
        lambda r: safe_div(r["valid_merchant_income"], r["promo_spend"]), axis=1
    )
    df["valid_order_gmv_roi"] = df.apply(
        lambda r: safe_div(r["valid_order_gmv"], r["promo_spend"]), axis=1
    )
    df["promo_cost_ratio"] = df.apply(
        lambda r: safe_div(r["promo_spend"], r["valid_merchant_income"]) * 100, axis=1
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

    # 有效订单拆分估算：按订单数比例拆分有效订单
    df["promo_valid_order_count"] = (
        df["promo_orders"] * df["valid_order_count"] / df["order_count"].replace(0, np.nan)
    ).fillna(0).round(0).astype(int)
    df["organic_valid_order_count"] = (df["valid_order_count"] - df["promo_valid_order_count"]).clip(lower=0).astype(int)
    df["organic_ratio_valid_orders"] = df.apply(
        lambda r: safe_div(r["organic_valid_order_count"], r["valid_order_count"]) * 100, axis=1
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
        for col in ["total_product_cost", "total_logistics_cost", "total_cost", "link_gross_profit", "profit_loss"]:
            if col in metrics.columns:
                cost_totals[col] = pd.to_numeric(metrics[col], errors="coerce").fillna(0).sum()
        if "valid_merchant_income" in metrics.columns and cost_totals.get("link_gross_profit") is not None:
            income = pd.to_numeric(metrics["valid_merchant_income"], errors="coerce").fillna(0).sum()
            cost_totals["gross_margin_rate"] = (cost_totals["link_gross_profit"] / income * 100) if income else 0.0
            cost_totals["profit_loss_rate"] = (cost_totals["profit_loss"] / income * 100) if income else 0.0

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
        "platform_fee": metrics["platform_fee"].sum() if "platform_fee" in metrics.columns else 0.0,
        "refund_count": metrics["refund_count"].sum(),
        "cancel_count": metrics["cancel_count"].sum(),
        "refund_unshipped_count": metrics.get("refund_unshipped_count", pd.Series(0, index=metrics.index)).sum(),
        "refund_shipped_count": metrics.get("refund_shipped_count", pd.Series(0, index=metrics.index)).sum(),
        "refund_received_count": metrics.get("refund_received_count", pd.Series(0, index=metrics.index)).sum(),
        "organic_orders": metrics["organic_orders"].sum(),
        "organic_gmv": metrics["organic_gmv"].sum(),
        "organic_merchant_income": metrics["organic_merchant_income"].sum(),
        "organic_valid_order_count": metrics["organic_valid_order_count"].sum(),
    }

    kpis = {
        "promo_spend": totals["promo_spend"],
        "promo_gmv": totals["promo_gmv"],
        "order_gmv": totals["order_gmv"],
        "valid_order_gmv": totals["valid_order_gmv"],
        "merchant_income": totals["merchant_income"],
        "valid_merchant_income": totals["valid_merchant_income"],
        "platform_fee": totals["platform_fee"],
        "promo_roi": safe_div(totals["promo_gmv"], totals["promo_spend"]),
        "real_roi": safe_div(totals["valid_merchant_income"], totals["promo_spend"]),
        "valid_order_gmv_roi": safe_div(totals["valid_order_gmv"], totals["promo_spend"]),
        "refund_rate": safe_div(totals["refund_count"], totals["order_count"]) * 100,
        "cancel_rate": safe_div(totals["cancel_count"], totals["order_count"]) * 100,
        "problem_rate": safe_div(
            totals["refund_count"] + totals["cancel_count"], totals["order_count"]
        ) * 100,
        "refund_unshipped_rate": safe_div(totals["refund_unshipped_count"], totals["order_count"]) * 100,
        "refund_shipped_rate": safe_div(totals["refund_shipped_count"], totals["order_count"]) * 100,
        "refund_received_rate": safe_div(totals["refund_received_count"], totals["order_count"]) * 100,
        "ctr": safe_div(totals["clicks"], totals["exposure"]) * 100,
        "click_to_order_rate": safe_div(totals["promo_orders"], totals["clicks"]) * 100,
        "exposure_to_order_rate": safe_div(totals["promo_orders"], totals["exposure"]) * 100,
        "cpc": safe_div(totals["promo_spend"], totals["clicks"]),
        "cpm": safe_div(totals["promo_spend"], totals["exposure"]) * 1000,
        "organic_ratio_gmv": safe_div(totals["organic_gmv"], totals["order_gmv"]) * 100,
        "organic_ratio_orders": safe_div(totals["organic_orders"], totals["order_count"]) * 100,
        "organic_merchant_income": totals["organic_merchant_income"],
        "organic_valid_order_count": totals["organic_valid_order_count"],
        "organic_ratio_income": safe_div(totals["organic_merchant_income"], totals["valid_merchant_income"]) * 100,
        "organic_ratio_valid_orders": safe_div(totals["organic_valid_order_count"], totals["valid_order_count"]) * 100,
        "promo_gmv_ratio": safe_div(totals["promo_gmv"], totals["order_gmv"]) * 100,
        "valid_order_gmv_ratio": safe_div(totals["valid_order_gmv"], totals["order_gmv"]) * 100,
        "promo_order_ratio": safe_div(totals["promo_orders"], totals["order_count"]) * 100,
        "promo_cost_ratio": safe_div(totals["promo_spend"], totals["valid_merchant_income"]) * 100,
        "exposure": totals["exposure"],
        "clicks": totals["clicks"],
        "order_count": totals["order_count"],
        "valid_order_count": totals["valid_order_count"],
        "promo_orders": totals["promo_orders"],
        "organic_orders": totals["organic_orders"],
        "organic_gmv": totals["organic_gmv"],
        "refund_count": totals["refund_count"],
        "cancel_count": totals["cancel_count"],
        "refund_unshipped_count": totals["refund_unshipped_count"],
        "refund_shipped_count": totals["refund_shipped_count"],
        "refund_received_count": totals["refund_received_count"],
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
        "merchant_income", "valid_merchant_income", "platform_fee",
        "refund_count", "cancel_count", "quantity", "valid_quantity",
        "organic_orders", "organic_gmv", "organic_merchant_income", "organic_valid_order_count",
    ]
    # 退款阶段字段若已存在则一起汇总
    for refund_col in ["refund_unshipped_count", "refund_shipped_count", "refund_received_count"]:
        if refund_col in combined.columns:
            sum_cols.append(refund_col)
    # 成本相关字段若已存在则一起汇总
    for cost_col in ["total_product_cost", "total_logistics_cost", "total_cost", "link_gross_profit", "profit_loss"]:
        if cost_col in combined.columns:
            sum_cols.append(cost_col)
    sum_cols = [c for c in sum_cols if c in combined.columns]

    agg = combined.groupby(group_cols, as_index=False)[sum_cols].sum()

    # 保留 product_id 用于后续匹配商家编码等
    if "product_id" in agg.columns:
        first_ids = combined.groupby(group_cols, as_index=False)["product_id"].first()
        agg = agg.merge(first_ids, on=group_cols, how="left", suffixes=("", "_first"))
        if "product_id_first" in agg.columns:
            agg["product_id"] = agg["product_id"].fillna(agg["product_id_first"])
            agg = agg.drop(columns=["product_id_first"])

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

    # 兼容旧数据：若订单明细缺少退款阶段标记，则根据订单状态补齐
    if "is_refund_unshipped" not in orders.columns:
        from data_processor import _classify_refund_stage
        orders = orders.copy()
        orders["refund_stage"] = orders.apply(
            lambda r: _classify_refund_stage(r) if r.get("is_refund") == 1 else "", axis=1
        )
        orders["is_refund_unshipped"] = (orders["refund_stage"] == "unshipped").astype(int)
        orders["is_refund_shipped"] = (orders["refund_stage"] == "shipped").astype(int)
        orders["is_refund_received"] = (orders["refund_stage"] == "received").astype(int)
        orders = orders.drop(columns=["refund_stage"])

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
        refund_unshipped_count=("is_refund_unshipped", "sum"),
        refund_shipped_count=("is_refund_shipped", "sum"),
        refund_received_count=("is_refund_received", "sum"),
    )

    agg["refund_rate"] = agg.apply(
        lambda r: safe_div(r["refund_count"], r["order_count"]) * 100, axis=1
    )
    agg["cancel_rate"] = agg.apply(
        lambda r: safe_div(r["cancel_count"], r["order_count"]) * 100, axis=1
    )
    agg["refund_unshipped_rate"] = agg.apply(
        lambda r: safe_div(r["refund_unshipped_count"], r["order_count"]) * 100, axis=1
    )
    agg["refund_shipped_rate"] = agg.apply(
        lambda r: safe_div(r["refund_shipped_count"], r["order_count"]) * 100, axis=1
    )
    agg["refund_received_rate"] = agg.apply(
        lambda r: safe_div(r["refund_received_count"], r["order_count"]) * 100, axis=1
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
