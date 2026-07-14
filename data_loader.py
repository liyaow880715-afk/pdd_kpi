"""
拼多多推广数据与订单数据读取模块
支持 .xls / .xlsx / .csv，自动识别编码，标准化列名
"""

import io
import pandas as pd
from typing import Dict, List, Tuple, Optional


# 列名别名映射： key -> [可能的列名]
COLUMN_ALIASES = {
    # 商品/样式标识
    "product_name": ["商品名称", "商品", "商品名", "宝贝名称"],
    "product_id": ["商品ID", "商品id", "商品Id", "宝贝ID", "宝贝id"],
    "merchant_code": ["商家编码", "商家代码", "商品编码", "链接编码"],
    "style_id": ["样式ID", "样式id", "样式Id", "SKUID", "sku_id", "SKU ID", "规格ID"],
    "style_name": ["商品规格", "规格", "SKU名称", "样式名称"],
    "group": ["分组", "计划组", "单元"],
    "plan_name": ["推广名称", "计划名称", "推广计划", "计划"],
    "bid_method": ["出价方式", "投放方式"],

    # 推广指标
    "promo_spend": ["成交花费(元)", "总花费(元)", "花费(元)", "消耗(元)", "推广花费"],
    "promo_gmv": ["交易额(元)", "成交金额(元)", "GMV(元)", "交易金额(元)"],
    "promo_orders": ["成交笔数", "成交订单数", "订单数", "成交量"],
    "promo_net_gmv": ["净交易额(元)", "净成交金额(元)"],
    "promo_net_orders": ["净成交笔数", "净成交订单数"],
    "promo_settle_gmv": ["结算交易额(元)", "结算成交金额(元)"],
    "promo_settle_orders": ["结算成交笔数", "结算成交订单数"],
    "exposure": ["曝光量", "曝光次数", "展现量"],
    "clicks": ["点击量", "点击次数", "点击数"],

    # 订单指标
    "order_status": ["订单状态", "状态"],
    "aftersales_status": ["售后状态", "售后"],
    "quantity": ["商品数量(件)", "数量", "购买数量"],
    "item_total": ["商品总价(元)", "商品总价"],
    "user_paid": ["用户实付金额(元)", "用户实付", "实付金额"],
    "merchant_income": ["商家实收金额(元)", "商家实收", "实收金额"],
    "platform_discount": ["平台优惠折扣(元)", "平台优惠"],
    "shop_discount": ["店铺优惠折扣(元)", "店铺优惠"],
    "pay_time": ["支付时间", "付款时间"],
    "order_time": ["订单成交时间", "成交时间", "下单时间"],
}


def _detect_encoding(file_bytes: bytes) -> str:
    """尝试用 chardet 检测编码，未安装则回退"""
    try:
        import chardet
        result = chardet.detect(file_bytes)
        return result.get("encoding") or "utf-8"
    except Exception:
        # 简单回退：优先尝试 UTF-8，否则 GBK
        try:
            file_bytes.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "gbk"


def _clean_column_name(name: str) -> str:
    """去除列名中的单位、括号、空格，用于模糊匹配"""
    name = str(name).strip()
    for s in ["(元)", "（元）", "(件)", "（件）", "(%)", "（%）", " "]:
        name = name.replace(s, "")
    return name


def _find_column(df_columns: pd.Index, aliases: List[str]) -> Optional[str]:
    """在 DataFrame 列名中查找第一个匹配的别名"""
    cols = [str(c).strip() for c in df_columns]

    # 1. 精确匹配
    for alias in aliases:
        alias_norm = str(alias).strip()
        if alias_norm in cols:
            return alias_norm

    # 2. 清洗后的包含匹配
    cleaned_cols = [_clean_column_name(c) for c in cols]
    for alias in aliases:
        alias_norm = str(alias).strip()
        alias_clean = _clean_column_name(alias_norm)
        if not alias_clean:
            continue
        for idx, c_clean in enumerate(cleaned_cols):
            if not c_clean:
                continue
            # alias 是列名的子串（如：成交花费 -> 成交花费(元)）
            if alias_clean in c_clean:
                return cols[idx]
            # 列名是 alias 的子串：要求列名长度 >=3，避免 商品 误匹配 商品id
            if len(c_clean) >= 3 and c_clean in alias_clean:
                return cols[idx]
    return None


def normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    标准化列名，返回新的 DataFrame 和映射字典。
    如果目标标准列名已经存在，则不再重命名其他列，避免产生重复列。
    """
    mapping: Dict[str, Optional[str]] = {}
    rename_map = {}
    for key, aliases in COLUMN_ALIASES.items():
        if key in df.columns:
            # 已经有标准列名，直接复用
            mapping[key] = key
            continue
        matched = _find_column(df.columns, aliases)
        mapping[key] = matched
        if matched:
            rename_map[matched] = key

    df = df.rename(columns=rename_map)
    return df, mapping


def read_promotion_file(file_obj) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    读取推广数据 Excel 文件
    :param file_obj: Streamlit UploadedFile 或文件路径
    :return: (DataFrame, 列名映射)
    """
    if hasattr(file_obj, "read"):
        bytes_data = file_obj.read()
        file_obj.seek(0)
    else:
        with open(file_obj, "rb") as f:
            bytes_data = f.read()

    # 尝试 xls / xlsx
    try:
        df = pd.read_excel(io.BytesIO(bytes_data))
    except Exception as e:
        raise ValueError(f"无法读取 Excel 推广文件: {e}")

    df, mapping = normalize_columns(df)

    # 保留原始列以便展示
    df["_source_type"] = "promotion"
    return df, mapping


def read_order_file(file_obj) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    读取订单 CSV 文件，自动识别编码
    """
    if hasattr(file_obj, "read"):
        bytes_data = file_obj.read()
        file_obj.seek(0)
    else:
        with open(file_obj, "rb") as f:
            bytes_data = f.read()

    encoding = _detect_encoding(bytes_data)

    # 尝试多种编码；若读取后出现重复列名，说明编码可能不对，继续尝试
    errors = []
    for enc in [encoding, "utf-8-sig", "utf-8", "gbk", "gb18030"]:
        try:
            df = pd.read_csv(io.BytesIO(bytes_data), encoding=enc, low_memory=False)
            if not df.columns.duplicated().any():
                break
            errors.append(f"{enc}: 出现重复列名")
        except Exception as e:
            errors.append(f"{enc}: {e}")
    else:
        raise ValueError(f"无法读取 CSV 订单文件，尝试过的编码：{errors}")

    df, mapping = normalize_columns(df)
    df["_source_type"] = "order"
    return df, mapping


def infer_date_from_filename(filename: str) -> Optional[str]:
    """从文件名推断日期，如 20260701 -> 2026-07-01"""
    import re
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None
