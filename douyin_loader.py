"""
抖音数据读取
- 支持 乘方推广/全域推广 等 Excel 文件
- 支持 抖音订单 CSV
- 将字段对齐为统一英文列名
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


MERCHANT_CODE_COLS = ["商家编码", "商家代码", "商品编码", "链接编码"]
SPEND_COLS = ["整体消耗", "综合成本"]
GMV_COLS = ["整体成交金额"]
VALID_GMV_COLS = ["净成交金额"]
ORDER_COUNT_COLS = ["整体成交订单数"]
VALID_ORDER_COUNT_COLS = ["净成交订单数"]
EXPOSURE_COLS = ["整体展示次数"]
CLICK_COLS = ["整体点击次数"]
REFUND_ORDER_COLS = ["1小时内退款订单数"]
REFUND_AMOUNT_COLS = ["1小时内退款金额"]


def _pick_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _parse_date(v: Any) -> Optional[str]:
    if pd.isna(v) or v is None:
        return None
    s = str(v).strip()
    if s in ("全部", "汇总", "总计", "-", ""):
        return None
    # 尝试常见日期格式
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y年%m月%d日 %H:%M:%S",
        "%Y年%m月%d日",
    )
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Excel 日期数字
    try:
        return pd.to_datetime(float(s), unit="D").strftime("%Y-%m-%d")
    except Exception:
        pass
    # 兜底：让 pandas 尝试解析（可处理 2026/7/4 这类非补零格式）
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def _clean_number(v: Any) -> float:
    if pd.isna(v):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in ("-", ""):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def read_promotion_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """读取抖音推广 Excel，返回统一列名的 DataFrame"""
    ext = filename.lower().split(".")[-1] if filename else "xlsx"
    if ext == "xls":
        df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
    else:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

    if df.empty:
        return df

    # 统一列名
    df = df.copy()
    df["product_id"] = df.get("商品ID", "").astype(str)
    df["product_name"] = df.get("商品名称", "").astype(str)
    df["date"] = df.get("日期", "").apply(_parse_date)

    spend_col = _pick_column(df, SPEND_COLS)
    gmv_col = _pick_column(df, GMV_COLS)
    valid_gmv_col = _pick_column(df, VALID_GMV_COLS)
    order_col = _pick_column(df, ORDER_COUNT_COLS)
    valid_order_col = _pick_column(df, VALID_ORDER_COUNT_COLS)
    exposure_col = _pick_column(df, EXPOSURE_COLS)
    click_col = _pick_column(df, CLICK_COLS)
    refund_order_col = _pick_column(df, REFUND_ORDER_COLS)
    refund_amount_col = _pick_column(df, REFUND_AMOUNT_COLS)

    df["spend"] = df[spend_col].apply(_clean_number) if spend_col else 0.0
    df["gmv"] = df[gmv_col].apply(_clean_number) if gmv_col else 0.0
    df["valid_gmv"] = df[valid_gmv_col].apply(_clean_number) if valid_gmv_col else df["gmv"]
    df["order_count"] = df[order_col].apply(_clean_number) if order_col else 0.0
    df["valid_order_count"] = df[valid_order_col].apply(_clean_number) if valid_order_col else df["order_count"]
    df["exposure"] = df[exposure_col].apply(_clean_number) if exposure_col else 0.0
    df["clicks"] = df[click_col].apply(_clean_number) if click_col else 0.0
    df["refund_orders"] = df[refund_order_col].apply(_clean_number) if refund_order_col else 0.0
    df["refund_amount"] = df[refund_amount_col].apply(_clean_number) if refund_amount_col else 0.0

    # 过滤汇总行（无日期）
    df = df[df["date"].notna()].copy()

    # 数值化
    numeric_cols = [
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "exposure", "clicks", "refund_orders", "refund_amount",
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df[[
        "product_id", "product_name", "date",
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "exposure", "clicks", "refund_orders", "refund_amount",
    ]]


def read_order_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """读取抖音订单 CSV，返回统一列名的 DataFrame"""
    encodings = ["utf-8", "utf-8-sig", "gb18030", "gbk"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError("无法解析订单 CSV 编码")

    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df["order_id"] = df.get("主订单编号", "").astype(str)
    df["sub_order_id"] = df.get("子订单编号", "").astype(str)
    df["product_id"] = df.get("商品ID", "").astype(str)
    df["product_name"] = df.get("选购商品", "").astype(str)
    df["spec"] = df.get("商品规格", "").astype(str)
    df["style_id"] = df.get("规格ID", "").astype(str) if "规格ID" in df.columns else df.get("style_id", "").astype(str) if "style_id" in df.columns else ""
    merchant_col = _pick_column(df, MERCHANT_CODE_COLS)
    df["merchant_code"] = df[merchant_col].astype(str) if merchant_col else ""
    df["quantity"] = pd.to_numeric(df.get("商品数量", 0), errors="coerce").fillna(0)
    df["price"] = df.get("商品单价", 0).apply(_clean_number)
    df["amount"] = df.get("订单应付金额", 0).apply(_clean_number)
    df["platform_subsidy"] = df.get("平台实际承担优惠金额", 0).apply(_clean_number)
    df["actual_revenue"] = df["amount"] + df["platform_subsidy"]
    df["order_status"] = df.get("订单状态", "").astype(str)
    df["aftersale_status"] = df.get("售后状态", "").astype(str)

    # 兼容多种时间列名
    time_col = _pick_column(df, ["订单提交时间", "下单时间", "订单创建时间", "创建时间", "付款时间", "支付时间"])
    df["order_time"] = df[time_col] if time_col else ""
    df["order_date"] = df["order_time"].apply(_parse_date)

    return df[[
        "order_id", "sub_order_id", "product_id", "product_name", "spec", "style_id", "merchant_code",
        "quantity", "price", "amount", "platform_subsidy", "actual_revenue",
        "order_status", "aftersale_status", "order_time", "order_date",
    ]]
