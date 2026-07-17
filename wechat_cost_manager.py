"""
微信小店成本管理
- 按自定义 SKU 编码维护商品成本/物流成本
- 存储文件：data/wechat_costs.json
- 应用成本时直接按 product_id（即 SKU 编码）左连接
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from wechat_storage import list_available_dates, list_wechat_stores, load_daily_orders

COSTS_FILE = Path("data/wechat_costs.json")


def _ensure_dir():
    COSTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_cost_config() -> Dict:
    _ensure_dir()
    if not COSTS_FILE.exists():
        return {}
    try:
        return json.loads(COSTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cost_config(config: Dict):
    _ensure_dir()
    config["updated_at"] = datetime.now().isoformat()
    COSTS_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_code(code) -> str:
    if pd.isna(code):
        return ""
    s = str(code).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _get_costs_dict(config: Optional[Dict] = None) -> Dict[str, Dict]:
    cfg = config or load_cost_config()
    return cfg.get("costs", {}) or {}


# ---------- 成本增删改查 ----------


def get_costs() -> List[Dict[str, Any]]:
    costs = _get_costs_dict()
    return [
        {
            "sku_code": code,
            "product_name": info.get("product_name", ""),
            "product_cost": float(info.get("product_cost", 0) or 0),
            "logistics_cost": float(info.get("logistics_cost", 0) or 0),
        }
        for code, info in costs.items()
    ]


def set_cost(
    config: Dict,
    sku_code: str,
    product_name: str = "",
    product_cost: float = 0.0,
    logistics_cost: float = 0.0,
) -> Dict:
    code = _normalize_code(sku_code)
    if not code:
        return config
    if "costs" not in config:
        config["costs"] = {}
    config["costs"][code] = {
        "product_name": str(product_name or "").strip(),
        "product_cost": float(product_cost or 0),
        "logistics_cost": float(logistics_cost or 0),
        "updated_at": datetime.now().isoformat(),
    }
    return config


def save_costs(costs: List[Dict[str, Any]]):
    cfg = load_cost_config()
    new_codes = set()
    for row in costs:
        code = _normalize_code(row.get("sku_code"))
        if not code:
            continue
        cfg = set_cost(
            cfg,
            sku_code=code,
            product_name=row.get("product_name", ""),
            product_cost=float(row.get("product_cost", 0) or 0),
            logistics_cost=float(row.get("logistics_cost", 0) or 0),
        )
        new_codes.add(code)
    # 删除已不存在的编码
    existing = _get_costs_dict(cfg)
    for code in list(existing.keys()):
        if code not in new_codes:
            existing.pop(code, None)
    save_cost_config(cfg)


# ---------- 导入/导出 ----------


def _normalize_cost_column_name(name: str) -> str:
    name = str(name).strip().replace(" ", "").replace("(元)", "").replace("（元）", "")
    mapping = {
        "SKU编码": "sku_code",
        "SKU": "sku_code",
        "sku": "sku_code",
        "skuid": "sku_code",
        "skucode": "sku_code",
        "自定义SKU": "sku_code",
        "自定义SKU编码": "sku_code",
        "商品名称": "product_name",
        "商品名": "product_name",
        "productname": "product_name",
        "商品成本": "product_cost",
        "商品成本/件": "product_cost",
        "成本": "product_cost",
        "productcost": "product_cost",
        "物流成本": "logistics_cost",
        "物流成本/件": "logistics_cost",
        "logisticscost": "logistics_cost",
    }
    return mapping.get(name, name)


def export_costs_to_csv(pending_only: bool = False) -> str:
    rows = get_costs()
    if pending_only:
        rows = [r for r in rows if (r.get("product_cost") or 0) <= 0 or (r.get("logistics_cost") or 0) <= 0]
    df = pd.DataFrame(rows, columns=["sku_code", "product_name", "product_cost", "logistics_cost"])
    df.columns = ["SKU编码", "商品名称", "商品成本/件", "物流成本/件"]
    return df.to_csv(index=False, encoding="utf-8-sig")


def import_costs_from_csv(file_bytes: bytes) -> int:
    df = None
    for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError("无法读取 CSV，请检查编码")

    rename = {}
    for col in df.columns:
        norm = _normalize_cost_column_name(col)
        if norm in ["sku_code", "product_name", "product_cost", "logistics_cost"]:
            rename[col] = norm
    df = df.rename(columns=rename)

    required = ["sku_code", "product_cost", "logistics_cost"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"CSV 缺少必要列：{col}")

    cfg = load_cost_config()
    count = 0
    for _, rec in df.iterrows():
        code = _normalize_code(rec.get("sku_code"))
        if not code:
            continue
        cfg = set_cost(
            cfg,
            sku_code=code,
            product_name=str(rec.get("product_name", "") or ""),
            product_cost=pd.to_numeric(rec.get("product_cost", 0), errors="coerce") or 0,
            logistics_cost=pd.to_numeric(rec.get("logistics_cost", 0), errors="coerce") or 0,
        )
        count += 1
    if count:
        save_cost_config(cfg)
    return count


# ---------- 刷新/未映射 ----------


def get_all_sku_codes() -> pd.DataFrame:
    codes = set()
    config = load_cost_config()
    costs = _get_costs_dict(config)
    for code in costs.keys():
        if code:
            codes.add(code)
    for store in list_wechat_stores():
        for d in list_available_dates(store):
            try:
                orders = load_daily_orders(store, d)
                if orders.empty or "sku_code" not in orders.columns:
                    continue
                for _, r in orders.iterrows():
                    code = _normalize_code(r.get("sku_code"))
                    if code:
                        codes.add(code)
            except Exception:
                continue
    if not codes:
        return pd.DataFrame(columns=["sku_code"])
    return pd.DataFrame(sorted(codes), columns=["sku_code"])


def refresh_cost_codes() -> Dict[str, int]:
    config = load_cost_config()
    existing = _get_costs_dict(config)
    detected = get_all_sku_codes()
    added = 0
    for code in detected["sku_code"].astype(str).tolist():
        code = _normalize_code(code)
        if not code or code in existing:
            continue
        config = set_cost(config, sku_code=code)
        added += 1
    if added:
        save_cost_config(config)
    return {"added": added}


def get_products_without_cost(
    store_names: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    stores = store_names if store_names else list_wechat_stores()
    config = load_cost_config()
    costs = _get_costs_dict(config)
    rows = []
    for store in stores:
        dates = list_available_dates(store)
        if start_date and end_date:
            dates = [d for d in dates if start_date <= d <= end_date]
        for d in dates:
            try:
                orders = load_daily_orders(store, d)
                if orders.empty or "sku_code" not in orders.columns:
                    continue
                for _, r in orders.iterrows():
                    code = _normalize_code(r.get("sku_code"))
                    if not code:
                        continue
                    if code in costs:
                        continue
                    rows.append({
                        "sku_code": code,
                        "product_name": str(r.get("product_name", "") or "").strip(),
                        "platform_sku_code": str(r.get("platform_sku_code", "") or "").strip(),
                        "store_name": store,
                        "date": d,
                    })
            except Exception:
                continue
    if not rows:
        return pd.DataFrame(columns=["sku_code", "product_name", "platform_sku_code", "store_name", "order_count", "first_date"])
    df = pd.DataFrame(rows)
    agg = df.groupby(["sku_code", "product_name", "platform_sku_code", "store_name"], as_index=False).agg(
        order_count=("date", "count"),
        first_date=("date", "min"),
    )
    return agg.sort_values(["order_count", "sku_code"], ascending=[False, True])


# ---------- 应用成本 ----------


def apply_costs_to_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics is None or metrics.empty:
        return metrics

    df = metrics.copy()
    config = load_cost_config()
    costs = _get_costs_dict(config)
    cost_df = pd.DataFrame([
        {"sku_code": code, **info}
        for code, info in costs.items()
    ])

    # 成本只按「自定义 SKU 编码」映射；空 SKU 的行不映射成本
    if "sku_code" not in df.columns:
        df["sku_code"] = ""
    df["sku_code"] = df["sku_code"].astype(str).str.strip().replace(["None", "nan", "NaN"], "")

    if not cost_df.empty:
        cost_df = cost_df.copy()
        cost_df["sku_code"] = cost_df["sku_code"].astype(str).str.strip()
        df = df.merge(
            cost_df[["sku_code", "product_cost", "logistics_cost"]],
            on="sku_code",
            how="left",
            suffixes=("", "_cost"),
        )
        df["product_cost_unit"] = pd.to_numeric(df.get("product_cost_cost", df.get("product_cost", 0)), errors="coerce").fillna(0)
        df["logistics_cost_unit"] = pd.to_numeric(df.get("logistics_cost_cost", df.get("logistics_cost", 0)), errors="coerce").fillna(0)
        for col in ["product_cost_cost", "logistics_cost_cost"]:
            if col in df.columns:
                df = df.drop(columns=[col])
    else:
        df["product_cost_unit"] = 0.0
        df["logistics_cost_unit"] = 0.0

    # 成本数量优先用「有效商品件数」，其次用「商品件数」
    if "valid_quantity" in df.columns:
        quantity = pd.to_numeric(df["valid_quantity"], errors="coerce").fillna(0)
    elif "quantity" in df.columns:
        quantity = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    else:
        quantity = pd.to_numeric(df.get("valid_order_count", 0), errors="coerce").fillna(0)

    income = pd.to_numeric(df.get("valid_gmv", 0), errors="coerce").fillna(0)

    df["total_product_cost"] = df["product_cost_unit"] * quantity
    df["total_logistics_cost"] = df["logistics_cost_unit"] * quantity
    df["total_cost"] = df["total_product_cost"] + df["total_logistics_cost"]
    df["gross_profit"] = income - df["total_cost"]
    df["profit_loss"] = df["gross_profit"]
    df["gross_margin_rate"] = df.apply(lambda r: (r["gross_profit"] / r["valid_gmv"] * 100) if r["valid_gmv"] else 0.0, axis=1)
    df["profit_loss_rate"] = df.apply(lambda r: (r["profit_loss"] / r["valid_gmv"] * 100) if r["valid_gmv"] else 0.0, axis=1)

    return df


def compute_cost_kpis(metrics: pd.DataFrame) -> Dict[str, float]:
    if metrics is None or metrics.empty:
        return {
            "total_cost": 0.0,
            "gross_profit": 0.0,
            "profit_loss": 0.0,
            "gross_margin_rate": 0.0,
            "profit_loss_rate": 0.0,
        }

    cols = ["total_cost", "gross_profit", "profit_loss", "valid_gmv"]
    for c in cols:
        if c not in metrics.columns:
            metrics[c] = 0.0
        else:
            metrics[c] = pd.to_numeric(metrics[c], errors="coerce").fillna(0)

    income = metrics["valid_gmv"].sum()
    profit = metrics["gross_profit"].sum()
    return {
        "total_cost": float(metrics["total_cost"].sum()),
        "gross_profit": float(profit),
        "profit_loss": float(metrics["profit_loss"].sum()),
        "gross_margin_rate": (profit / income * 100) if income else 0.0,
        "profit_loss_rate": (metrics["profit_loss"].sum() / income * 100) if income else 0.0,
    }
