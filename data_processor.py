"""
数据匹配与处理：将推广数据和订单数据按商品ID/样式ID对齐
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


ORDER_STATUS_REFUND = {
    "已发货，退款成功",
    "已收货，退款成功",
    "未发货，退款成功",
    "退款成功",
    "售后中",
}
ORDER_STATUS_CANCEL = {
    "已取消",
    "取消",
    "交易关闭",
}


def _clean_product_id(val):
    """清理商品ID，统一为整数或字符串"""
    if pd.isna(val) or val in ("-", "", " "):
        return None
    try:
        # 尝试转整数
        return int(float(val))
    except Exception:
        return str(val).strip()


def _clean_style_id(val):
    """清理样式ID"""
    if pd.isna(val) or val in ("-", "", " "):
        return None
    try:
        return int(float(val))
    except Exception:
        return str(val).strip()


def _is_refund(row) -> int:
    """判断是否为退款订单"""
    status = str(row.get("order_status", ""))
    aftersales = str(row.get("aftersales_status", ""))
    if "退款成功" in status or "退款成功" in aftersales or "售后中" in status:
        return 1
    return 0


def _is_cancel(row) -> int:
    """判断是否为取消订单"""
    status = str(row.get("order_status", ""))
    if any(s in status for s in ["已取消", "取消", "交易关闭"]):
        return 1
    return 0


def preprocess_orders(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    """
    预处理订单数据：标准化 ID、计算退款/取消标记
    """
    df = df.copy()

    # 标准化列名用于后续处理
    col_renames = {}
    if mapping.get("order_status"):
        col_renames[mapping["order_status"]] = "order_status"
    if mapping.get("aftersales_status"):
        col_renames[mapping["aftersales_status"]] = "aftersales_status"

    # 已经通过 normalize_columns 改名，这里确保原始名也保留用于安全
    if "order_status" not in df.columns and "订单状态" in df.columns:
        df["order_status"] = df["订单状态"]
    if "aftersales_status" not in df.columns and "售后状态" in df.columns:
        df["aftersales_status"] = df["售后状态"]

    # 标准化 ID 列
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].apply(_clean_product_id)
    if "style_id" in df.columns:
        df["style_id"] = df["style_id"].apply(_clean_style_id)

    # 金额/数量转数值
    for col in ["item_total", "user_paid", "merchant_income", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 重命名方便后续聚合
    rename_map = {
        "订单号": "order_id",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 商品名称/规格名称（normalize_columns 已改名，这里保留 raw 名用于聚合展示）
    if "product_name" in df.columns:
        df["product_name_raw"] = df["product_name"]
    if "style_name" in df.columns:
        df["style_name_raw"] = df["style_name"]

    if "order_id" not in df.columns:
        df["order_id"] = df.index.astype(str)

    # 退款/取消标记
    df["is_refund"] = df.apply(_is_refund, axis=1)
    df["is_cancel"] = df.apply(_is_cancel, axis=1)
    df["is_valid"] = ((df["is_refund"] == 0) & (df["is_cancel"] == 0)).astype(int)

    return df


def preprocess_promotion(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    """
    预处理推广数据：标准化 ID、数值列
    """
    df = df.copy()

    # 过滤合计行（通过商品ID或名称为 - / 总计 / 合计）
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].apply(_clean_product_id)
        # 保留有效商品ID
        df = df[df["product_id"].notna()].copy()

    if "style_id" in df.columns:
        df["style_id"] = df["style_id"].apply(_clean_style_id)

    # 数值列
    numeric_cols = [
        "promo_spend", "promo_gmv", "promo_orders",
        "promo_net_gmv", "promo_net_orders",
        "promo_settle_gmv", "promo_settle_orders",
        "exposure", "clicks"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def aggregate_orders_by_product(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """按商品ID聚合订单"""
    agg = orders.groupby("product_id", as_index=False).agg(
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
    # 取第一个商品名称
    names = orders.groupby("product_id")["product_name_raw"].first().reset_index()
    names.columns = ["product_id", "product_name_raw"]
    agg = agg.merge(names, on="product_id", how="left")
    return agg


def aggregate_orders_by_style(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """按商品ID + 样式ID聚合订单"""
    group_cols = ["product_id"]
    if "style_id" in orders.columns and orders["style_id"].notna().any():
        group_cols.append("style_id")
    else:
        # 无样式ID时退回到按商品聚合
        return aggregate_orders_by_product(orders)

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

    # 取名称
    name_cols = ["product_id"]
    if "style_id" in group_cols:
        name_cols.append("style_id")
    names = orders.groupby(name_cols, as_index=False).agg(
        product_name_raw=("product_name_raw", "first"),
        style_name_raw=("style_name_raw", "first"),
    )
    agg = agg.merge(names, on=name_cols, how="left")
    return agg


def aggregate_promotion_by_product(promo: pd.DataFrame) -> pd.DataFrame:
    """按商品ID聚合推广数据"""
    cols = ["product_id"]
    if "style_id" in promo.columns and promo["style_id"].notna().any():
        cols.append("style_id")

    agg_dict = {
        "promo_spend": "sum",
        "promo_gmv": "sum",
        "promo_orders": "sum",
        "promo_net_gmv": "sum",
        "promo_net_orders": "sum",
        "promo_settle_gmv": "sum",
        "promo_settle_orders": "sum",
        "exposure": "sum",
        "clicks": "sum",
    }
    agg_dict = {k: v for k, v in agg_dict.items() if k in promo.columns}

    agg = promo.groupby(cols, as_index=False).agg(agg_dict)

    # 名称
    name_cols = ["product_id"]
    if "style_id" in cols:
        name_cols.append("style_id")
    name_dict = {"product_name": "first"}
    if "style_name" in promo.columns:
        name_dict["style_name"] = "first"
    names = promo.groupby(name_cols, as_index=False).agg(name_dict)
    agg = agg.merge(names, on=name_cols, how="left")
    return agg


def match_promotion_and_orders(
    promo_df: pd.DataFrame,
    order_df: pd.DataFrame,
    promo_mapping: Dict[str, Optional[str]],
    order_mapping: Dict[str, Optional[str]],
    date: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    匹配推广数据与订单数据
    :return: (商品级指标, 样式级指标, 原始处理后的订单数据)
    """
    promo = preprocess_promotion(promo_df, promo_mapping)
    orders = preprocess_orders(order_df, order_mapping)

    # 推广聚合
    promo_agg = aggregate_promotion_by_product(promo)

    # 判断是否有样式维度
    has_style = "style_id" in promo_agg.columns and promo_agg["style_id"].notna().any()

    if has_style:
        order_agg = aggregate_orders_by_style(orders)
        merged = pd.merge(
            promo_agg,
            order_agg,
            on=["product_id", "style_id"],
            how="outer",
            suffixes=("", "_order"),
        )
        # 名称合并
        merged["product_name"] = merged["product_name"].fillna(merged["product_name_raw"])
        if "style_name" in merged.columns:
            merged["style_name"] = merged["style_name"].fillna(merged.get("style_name_raw"))
    else:
        order_agg = aggregate_orders_by_product(orders)
        merged = pd.merge(
            promo_agg,
            order_agg,
            on="product_id",
            how="outer",
            suffixes=("", "_order"),
        )
        merged["product_name"] = merged["product_name"].fillna(merged["product_name_raw"])

    # 填充缺失的推广/订单指标为 0
    for col in ["promo_spend", "promo_gmv", "promo_orders", "exposure", "clicks"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)
    order_cols = [
        "order_count", "valid_order_count",
        "order_gmv", "valid_order_gmv",
        "user_paid", "valid_user_paid",
        "merchant_income", "valid_merchant_income",
        "refund_count", "cancel_count",
        "quantity", "valid_quantity"
    ]
    for col in order_cols:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    # 添加日期
    if date:
        merged["date"] = date
        order_agg["date"] = date

    # 样式级聚合（从订单侧，用于样式分析页）
    style_metrics = aggregate_orders_by_style(orders)
    if date:
        style_metrics["date"] = date

    return merged, style_metrics, orders
