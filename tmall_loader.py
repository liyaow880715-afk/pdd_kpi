"""
天猫数据读取
- 支持天猫推广计划 CSV（计划维度，含预售/直接/间接成交）
- 支持天猫订单明细 Excel
- 将字段对齐为统一英文列名
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


def _parse_date(v: Any) -> Optional[str]:
    if pd.isna(v) or v is None:
        return None
    s = str(v).strip()
    if s in ("全部", "汇总", "总计", "-", ""):
        return None
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
    try:
        return pd.to_datetime(float(s), unit="D").strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def _parse_datetime(v: Any) -> Optional[str]:
    if pd.isna(v) or v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-",):
        return None
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return s


def _clean_number(v: Any) -> float:
    if pd.isna(v):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").replace("¥", "").strip()
    if s in ("-", ""):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def read_promotion_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """读取天猫推广计划 CSV，返回统一列名的 DataFrame"""
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError("无法解析天猫推广 CSV 编码")

    if df.empty:
        return df

    df = df.copy()
    # 清理列名首尾空格，避免 CSV 列名带空格导致映射失败
    df.columns = [str(c).strip() for c in df.columns]

    # 列名统一
    df["date"] = df.get("日期", "").apply(_parse_date)
    df["plan_id"] = df.get("计划ID", "").astype(str)
    df["plan_name"] = df.get("计划名字", "").astype(str)

    # 核心推广指标
    numeric_map = {
        "spend": "花费",
        "exposure": "展现量",
        "clicks": "点击量",
        "gmv": "总成交金额",
        "order_count": "总成交笔数",
        "direct_gmv": "直接成交金额",
        "indirect_gmv": "间接成交金额",
        "direct_order_count": "直接成交笔数",
        "indirect_order_count": "间接成交笔数",
        "cart_count": "总购物车数",
        "collect_count": "总收藏数",
        "presell_gmv": "总预售成交金额",
        "presell_order_count": "总预售成交笔数",
    }
    for eng, chn in numeric_map.items():
        df[eng] = df[chn].apply(_clean_number) if chn in df.columns else 0.0

    # 过滤汇总行（无日期）
    df = df[df["date"].notna()].copy()

    # 使用计划 ID 作为商品维度 key
    df["product_id"] = df["plan_id"]
    df["product_name"] = df["plan_name"]

    # 计算有效 GMV：总成交金额 + 预售成交金额
    df["valid_gmv"] = df["gmv"] + df["presell_gmv"]
    df["valid_order_count"] = df["order_count"] + df["presell_order_count"]

    # 退款/金额相关：推广数据没有退款，默认 0
    df["refund_orders"] = 0.0
    df["refund_amount"] = 0.0

    for c in ["spend", "exposure", "clicks", "gmv", "order_count", "valid_gmv", "valid_order_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df[[
        "product_id", "product_name", "plan_id", "plan_name", "date",
        "spend", "gmv", "valid_gmv", "order_count", "valid_order_count",
        "direct_gmv", "indirect_gmv", "direct_order_count", "indirect_order_count",
        "exposure", "clicks", "presell_gmv", "presell_order_count",
        "cart_count", "collect_count", "refund_orders", "refund_amount",
    ]]


def read_order_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """读取天猫订单 Excel，返回统一列名的 DataFrame"""
    ext = filename.lower().split(".")[-1] if filename else "xlsx"
    if ext == "xls":
        df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
    else:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    df["order_id"] = df.get("订单编号", "").astype(str)
    df["product_name"] = df.get("商品标题", "").astype(str)
    df["spec"] = df.get("商品属性SKU", "").astype(str)
    # 用商品标题作为 product_id，SKU 作为 style_id，方便成本/未映射检测
    df["product_id"] = df["product_name"]
    df["style_id"] = df["spec"]
    df["merchant_code"] = df.get("商家编码", "").astype(str)
    df["quantity"] = pd.to_numeric(df.get("宝贝总数量", 0), errors="coerce").fillna(0)
    df["amount"] = df.get("买家实付金额", 0).apply(_clean_number)
    df["actual_revenue"] = df["amount"]
    df["refund_amount"] = df.get("退款金额", 0).apply(_clean_number)
    df["compensation_amount"] = df.get("赔付金额", 0).apply(_clean_number)
    df["order_status"] = df.get("订单状态", "").astype(str)

    # 时间字段
    time_col = "订单付款时间" if "订单付款时间" in df.columns else None
    if not time_col and "订单创建时间" in df.columns:
        time_col = "订单创建时间"
    df["order_time"] = df[time_col].apply(_parse_datetime) if time_col else ""
    df["order_date"] = df["order_time"].apply(_parse_date)

    return df[[
        "order_id", "product_id", "style_id", "product_name", "spec", "merchant_code",
        "quantity", "amount", "actual_revenue", "refund_amount", "compensation_amount",
        "order_status", "order_time", "order_date",
    ]]
