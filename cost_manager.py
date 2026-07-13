"""
商品成本与物流成本管理
- 根据订单中的商家编码维护成本
- 将成本应用到商品指标，计算链接毛利与盈亏
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from storage import list_available_dates, load_daily_orders


DATA_DIR = Path("data")
COSTS_FILE = DATA_DIR / "costs.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_cost_config() -> Dict:
    """加载成本配置"""
    _ensure_dir()
    if not COSTS_FILE.exists():
        return {"merchant_costs": {}}
    try:
        return json.loads(COSTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"merchant_costs": {}}


def save_cost_config(config: Dict):
    """保存成本配置"""
    _ensure_dir()
    COSTS_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_store(store_name: Optional[str]) -> str:
    return str(store_name or "默认店铺").strip()


def _normalize_code(code) -> str:
    if pd.isna(code):
        return ""
    return str(code).strip()


def get_cost(config: Dict, store_name: Optional[str], merchant_code: str) -> Dict:
    """获取某个商家编码的成本"""
    store = _normalize_store(store_name)
    code = _normalize_code(merchant_code)
    costs = config.get("merchant_costs", {}).get(store, {})
    return costs.get(code, {
        "product_name": "",
        "product_cost": 0.0,
        "logistics_cost": 0.0,
        "updated_at": "",
    })


def set_cost(
    config: Dict,
    store_name: Optional[str],
    merchant_code: str,
    product_name: str = "",
    product_cost: float = 0.0,
    logistics_cost: float = 0.0,
) -> Dict:
    """设置某个商家编码的成本"""
    store = _normalize_store(store_name)
    code = _normalize_code(merchant_code)
    if not code:
        return config

    if "merchant_costs" not in config:
        config["merchant_costs"] = {}
    if store not in config["merchant_costs"]:
        config["merchant_costs"][store] = {}

    config["merchant_costs"][store][code] = {
        "product_name": str(product_name or "").strip(),
        "product_cost": float(product_cost or 0),
        "logistics_cost": float(logistics_cost or 0),
        "updated_at": datetime.now().isoformat(),
    }
    return config


def delete_cost(config: Dict, store_name: Optional[str], merchant_code: str) -> Dict:
    """删除某个商家编码的成本"""
    store = _normalize_store(store_name)
    code = _normalize_code(merchant_code)
    config.get("merchant_costs", {}).get(store, {}).pop(code, None)
    return config


def list_store_costs(config: Dict, store_name: Optional[str]) -> List[Dict]:
    """列出某店铺下所有成本配置"""
    store = _normalize_store(store_name)
    costs = config.get("merchant_costs", {}).get(store, {})
    rows = []
    for code, info in costs.items():
        rows.append({"merchant_code": code, **info})
    return rows


def _find_merchant_code_column(orders: pd.DataFrame) -> Optional[str]:
    """兼容新旧数据，找到商家编码所在列"""
    if "merchant_code" in orders.columns:
        return "merchant_code"
    for col in orders.columns:
        col_str = str(col).strip()
        if col_str in ("商家编码", "商家代码", "商品编码", "链接编码"):
            return col_str
    return None


def extract_merchant_codes_from_orders(store_name: Optional[str]) -> pd.DataFrame:
    """
    从历史订单中提取所有商家编码（仅用于追加新编码，不考虑商品名称）
    兼容旧数据：原始列名如「商家编码」也能识别。
    返回 DataFrame：merchant_code
    """
    store = _normalize_store(store_name)
    dates = list_available_dates(store)
    codes = set()

    for d in dates:
        try:
            orders = load_daily_orders(d, store)
            if orders.empty:
                continue
            code_col = _find_merchant_code_column(orders)
            if not code_col:
                continue
            for _, r in orders.iterrows():
                code = _normalize_code(r.get(code_col))
                if not code:
                    continue
                codes.add(code)
        except Exception:
            continue

    if not codes:
        return pd.DataFrame(columns=["merchant_code"])

    return pd.DataFrame(sorted(codes), columns=["merchant_code"])


def append_new_merchant_codes(store_name: Optional[str]) -> int:
    """
    把订单中出现、但成本配置里还不存在的商家编码追加进去。
    已存在的编码不会被覆盖（成本、名称都保留）。
    返回新增编码数量。
    """
    store = _normalize_store(store_name)
    cfg = load_cost_config()
    saved = cfg.get("merchant_costs", {}).get(store, {})
    detected_df = extract_merchant_codes_from_orders(store)

    if detected_df.empty:
        return 0

    added = 0
    for code in detected_df["merchant_code"]:
        code = _normalize_code(code)
        if not code or code in saved:
            continue
        cfg = set_cost(cfg, store_name=store, merchant_code=code)
        added += 1

    if added:
        save_cost_config(cfg)
    return added


def _build_product_id_to_merchant_code(store_name: Optional[str]) -> Dict[str, str]:
    """从历史订单中建立 product_id -> merchant_code 映射（用于旧数据回退）"""
    store = _normalize_store(store_name)
    mapping = {}
    dates = list_available_dates(store)
    for d in dates:
        try:
            orders = load_daily_orders(d, store)
            code_col = _find_merchant_code_column(orders)
            if not code_col or "product_id" not in orders.columns:
                continue
            for _, r in orders.iterrows():
                pid = r.get("product_id")
                code = _normalize_code(r.get(code_col))
                if pd.notna(pid) and code and str(pid) not in mapping:
                    mapping[str(pid)] = code
        except Exception:
            continue
    return mapping


def apply_costs_to_metrics(metrics: pd.DataFrame, store_name: Optional[str]) -> pd.DataFrame:
    """
    将成本配置合并到商品指标表，并计算链接毛利与盈亏。
    如果指标表里没有 merchant_code，会尝试用 product_id 从历史订单反查。
    """
    if metrics is None or metrics.empty:
        return metrics

    df = metrics.copy()
    config = load_cost_config()
    store = _normalize_store(store_name)
    costs = config.get("merchant_costs", {}).get(store, {})

    if not costs:
        df["product_cost_unit"] = 0.0
        df["logistics_cost_unit"] = 0.0
        df["total_cost"] = 0.0
        df["link_gross_profit"] = df.get("valid_merchant_income", 0)
        df["profit_loss"] = df["link_gross_profit"] - df.get("promo_spend", 0)
        df["gross_margin_rate"] = 0.0
        return df

    cost_df = pd.DataFrame([
        {"merchant_code": code, **info}
        for code, info in costs.items()
    ])

    # 确保 merchant_code 列为字符串
    if "merchant_code" in df.columns:
        df["merchant_code"] = df["merchant_code"].astype(str).str.strip()
    else:
        df["merchant_code"] = ""

    # 旧数据回退：用 product_id 反查商家编码
    merchant_codes_blank = df["merchant_code"].replace("", pd.NA).isna()
    if merchant_codes_blank.any() and "product_id" in df.columns:
        mapping = _build_product_id_to_merchant_code(store_name)
        if mapping:
            df.loc[merchant_codes_blank, "merchant_code"] = (
                df.loc[merchant_codes_blank, "product_id"]
                .astype(str)
                .map(mapping)
            )
    df["merchant_code"] = df["merchant_code"].fillna("").astype(str).str.strip()

    df = df.merge(
        cost_df[["merchant_code", "product_cost", "logistics_cost"]],
        on="merchant_code",
        how="left",
        suffixes=("", "_cost"),
    )

    df["product_cost_unit"] = pd.to_numeric(df.get("product_cost_cost", df.get("product_cost", 0)), errors="coerce").fillna(0)
    df["logistics_cost_unit"] = pd.to_numeric(df.get("logistics_cost_cost", df.get("logistics_cost", 0)), errors="coerce").fillna(0)

    # 成本按有效件数计算；如果没有件数则按有效订单数
    quantity_col = "valid_quantity" if "valid_quantity" in df.columns else "valid_order_count"
    df["cost_quantity"] = pd.to_numeric(df.get(quantity_col, 0), errors="coerce").fillna(0)

    df["total_product_cost"] = df["product_cost_unit"] * df["cost_quantity"]
    df["total_logistics_cost"] = df["logistics_cost_unit"] * df["cost_quantity"]
    df["total_cost"] = df["total_product_cost"] + df["total_logistics_cost"]

    df["valid_merchant_income"] = pd.to_numeric(df.get("valid_merchant_income", 0), errors="coerce").fillna(0)
    df["promo_spend"] = pd.to_numeric(df.get("promo_spend", 0), errors="coerce").fillna(0)

    df["link_gross_profit"] = df["valid_merchant_income"] - df["total_cost"]
    df["profit_loss"] = df["link_gross_profit"] - df["promo_spend"]
    df["gross_margin_rate"] = df.apply(
        lambda r: (r["link_gross_profit"] / r["valid_merchant_income"] * 100)
        if r["valid_merchant_income"] else 0.0,
        axis=1,
    )

    # 清理临时列
    for col in ["product_cost_cost", "logistics_cost_cost"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    return df


def compute_cost_kpis(metrics: pd.DataFrame) -> Dict[str, float]:
    """从已应用成本的成本指标中汇总成本相关 KPI"""
    if metrics is None or metrics.empty:
        return {
            "total_cost": 0.0,
            "link_gross_profit": 0.0,
            "profit_loss": 0.0,
            "gross_margin_rate": 0.0,
        }

    cols = ["total_cost", "link_gross_profit", "profit_loss", "valid_merchant_income"]
    for c in cols:
        if c not in metrics.columns:
            metrics[c] = 0.0
        else:
            metrics[c] = pd.to_numeric(metrics[c], errors="coerce").fillna(0)

    income = metrics["valid_merchant_income"].sum()
    profit = metrics["link_gross_profit"].sum()
    return {
        "total_cost": metrics["total_cost"].sum(),
        "link_gross_profit": profit,
        "profit_loss": metrics["profit_loss"].sum(),
        "gross_margin_rate": (profit / income * 100) if income else 0.0,
    }
