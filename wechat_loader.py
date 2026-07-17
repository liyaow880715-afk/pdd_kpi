"""
微信小店订单数据读取
- 只支持订单 Excel 导入
- 将字段对齐为统一英文列名
"""

import io
from datetime import datetime
from typing import Any, List, Optional

import pandas as pd


SKU_CUSTOM_CODE_COLS = [
    "SKU编码(自定义)",
    "SKU编码（自定义）",
    "自定义SKU编码",
    "自定义SKU",
    "SKUCODE（自定义）",
]

PLATFORM_SKU_CODE_COLS = [
    "SKU编码(平台)",
    "SKU编码（平台）",
    "平台SKU编码",
    "SKU编码",
    "SKUID",
    "平台SKUID",
]

PLATFORM_PRODUCT_ID_COLS = [
    "商品ID",
    "商品编号",
    "SPUID",
    "商品ID（平台）",
    "平台商品ID",
]


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
    s = str(v).replace(",", "").replace("%", "").replace("¥", "").replace("元", "").strip()
    if s in ("-", ""):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def read_order_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """读取微信小店订单 Excel，返回统一列名的 DataFrame"""
    ext = filename.lower().split(".")[-1] if filename else "xlsx"
    if ext == "xls":
        df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
    else:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 基础字段
    df["order_id"] = df.get("订单号", "").astype(str)
    df["product_name"] = df.get("商品名称", "").astype(str)
    df["order_status"] = df.get("订单状态", "").astype(str)

    # 时间字段
    df["order_time"] = df.get("订单下单时间", "").apply(_parse_datetime)
    df["order_date"] = df.get("订单下单时间", "").apply(_parse_date)

    # SKU / 商品编码
    sku_custom_col = _pick_column(df, SKU_CUSTOM_CODE_COLS)
    platform_sku_col = _pick_column(df, PLATFORM_SKU_CODE_COLS)
    platform_product_col = _pick_column(df, PLATFORM_PRODUCT_ID_COLS)

    df["sku_code"] = df[sku_custom_col].astype(str).str.strip() if sku_custom_col else ""
    df["platform_sku_code"] = df[platform_sku_col].astype(str).str.strip() if platform_sku_col else ""
    df["platform_product_id"] = df[platform_product_col].astype(str).str.strip() if platform_product_col else ""

    # product_id：成本映射只认自定义 SKU；若自定义 SKU 为空，则回退到平台 SKU/商品 ID 仅用于分组展示
    df["product_id"] = df["sku_code"].replace("", pd.NA)
    df["product_id"] = df["product_id"].fillna(df["platform_sku_code"])
    df["product_id"] = df["product_id"].fillna(df["platform_product_id"])
    df["product_id"] = df["product_id"].fillna(df["product_name"]).fillna("").astype(str)

    # 金额字段
    df["quantity"] = pd.to_numeric(df.get("商品数量", 0), errors="coerce").fillna(0)
    df["amount"] = df.get("订单实际支付金额", 0).apply(_clean_number)
    df["actual_revenue"] = df.get("订单实际收款金额", 0).apply(_clean_number)
    df["refund_amount"] = df.get("商品已退款金额", 0).apply(_clean_number)
    df["tech_fee"] = df.get("技术服务费", 0).apply(_clean_number)
    df["commission"] = df.get("带货费用", 0).apply(_clean_number)

    df["net_revenue"] = df["actual_revenue"] - df["refund_amount"] - df["tech_fee"] - df["commission"]

    # 有效订单：实际收款 > 0 且状态不包含取消/关闭
    invalid_status = df["order_status"].astype(str).str.contains("取消|关闭", na=False)
    df["is_valid"] = (df["actual_revenue"] > 0) & (~invalid_status)

    # KOL 信息
    df["kol_name"] = df.get("带货账号昵称", "").astype(str)
    df["kol_id"] = df.get("带货ID", "").astype(str)
    df["channel"] = df.get("带货方式", "").astype(str)

    return df[[
        "order_id", "order_date", "order_time", "order_status",
        "product_id", "product_name", "sku_code", "platform_sku_code", "platform_product_id",
        "quantity", "amount", "actual_revenue", "refund_amount",
        "tech_fee", "commission", "net_revenue", "is_valid",
        "kol_name", "kol_id", "channel",
    ]]
