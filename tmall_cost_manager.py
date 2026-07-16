"""
天猫成本管理（与抖音成本管理对齐）
- 按商家编码维护商品成本/物流成本（全店铺通用）
- 支持 product_id / style_id -> 商家编码 映射
- 支持从订单中刷新商家编码、识别未映射商品
- 支持导入/导出 CSV、导出待维护编码
- 存储文件：data/tmall_costs.json
- 应用成本时收入基于 valid_gmv，数量基于 valid_quantity
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from tmall_storage import list_available_dates, list_tmall_stores, load_daily_orders

COSTS_FILE = Path("data/tmall_costs.json")

GLOBAL_COSTS_KEY = "global_merchant_costs"
GLOBAL_PRODUCT_MAP_KEY = "global_product_merchant_map"
GLOBAL_STYLE_MAP_KEY = "global_style_merchant_map"


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
    return str(code).strip()


def _normalize_product_id(pid) -> str:
    if pd.isna(pid):
        return ""
    s = str(pid).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _normalize_style_id(sid) -> str:
    if pd.isna(sid):
        return ""
    s = str(sid).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _style_map_key(product_id, style_id) -> str:
    return f"{_normalize_product_id(product_id)}::{_normalize_style_id(style_id)}"


def _find_merchant_code_column(orders: pd.DataFrame) -> Optional[str]:
    if "merchant_code" in orders.columns:
        return "merchant_code"
    for col in orders.columns:
        col_str = str(col).strip()
        if col_str in ("商家编码", "商家代码", "商品编码", "链接编码"):
            return col_str
    return None


def _find_style_columns(orders: pd.DataFrame) -> Dict[str, Optional[str]]:
    result = {"style_id_col": None, "style_name_col": None, "spec_col": None}
    cols = [str(c).strip() for c in orders.columns]
    for col in cols:
        if col.lower() in ("style_id", "样式id", "款式id", "styleid"):
            result["style_id_col"] = col
        if col in ("style_name", "样式名称", "款式名称", "商品规格"):
            result["style_name_col"] = col
        if col in ("商品规格", "规格", "sku", "specification"):
            result["spec_col"] = col
    return result


# ---------- 全局商家编码成本 ----------


def load_global_costs(config: Optional[Dict] = None) -> Dict[str, Dict]:
    cfg = config or load_cost_config()
    return cfg.get(GLOBAL_COSTS_KEY, {}) or {}


def save_global_cost(
    config: Dict,
    merchant_code: str,
    product_name: str = "",
    product_cost: float = 0.0,
    logistics_cost: float = 0.0,
) -> Dict:
    code = _normalize_code(merchant_code)
    if not code:
        return config
    if GLOBAL_COSTS_KEY not in config:
        config[GLOBAL_COSTS_KEY] = {}
    config[GLOBAL_COSTS_KEY][code] = {
        "product_name": str(product_name or "").strip(),
        "product_cost": float(product_cost or 0),
        "logistics_cost": float(logistics_cost or 0),
        "updated_at": datetime.now().isoformat(),
    }
    return config


def delete_global_cost(config: Dict, merchant_code: str) -> Dict:
    code = _normalize_code(merchant_code)
    config.get(GLOBAL_COSTS_KEY, {}).pop(code, None)
    return config


def list_global_cost_rows(config: Optional[Dict] = None) -> List[Dict]:
    costs = load_global_costs(config)
    return [{"merchant_code": code, **info} for code, info in costs.items()]


def get_global_costs() -> List[Dict[str, Any]]:
    return list_global_cost_rows()


def save_global_costs(costs: List[Dict[str, Any]]):
    cfg = load_cost_config()
    existing = load_global_costs(cfg)
    for row in costs:
        code = _normalize_code(row.get("merchant_code"))
        if not code:
            continue
        cfg = save_global_cost(
            cfg,
            merchant_code=code,
            product_name=row.get("product_name", ""),
            product_cost=float(row.get("product_cost", 0) or 0),
            logistics_cost=float(row.get("logistics_cost", 0) or 0),
        )
    # 删除已不存在的编码
    new_codes = {_normalize_code(r.get("merchant_code")) for r in costs if _normalize_code(r.get("merchant_code", ""))}
    for code in list(existing.keys()):
        if code not in new_codes:
            cfg = delete_global_cost(cfg, code)
    save_cost_config(cfg)


# ---------- 商品/规格 -> 商家编码 映射 ----------


def load_global_product_mapping(config: Optional[Dict] = None) -> Dict[str, str]:
    cfg = config or load_cost_config()
    return cfg.get(GLOBAL_PRODUCT_MAP_KEY, {}) or {}


def save_global_product_mapping(
    config: Dict,
    product_id,
    merchant_code: str,
    style_id=None,
    product_name: str = "",
) -> Dict:
    pid = _normalize_product_id(product_id)
    sid = _normalize_style_id(style_id)
    code = _normalize_code(merchant_code)
    if not code or not pid:
        return config

    if sid:
        if GLOBAL_STYLE_MAP_KEY not in config:
            config[GLOBAL_STYLE_MAP_KEY] = {}
        config[GLOBAL_STYLE_MAP_KEY][_style_map_key(pid, sid)] = code
    else:
        if GLOBAL_PRODUCT_MAP_KEY not in config:
            config[GLOBAL_PRODUCT_MAP_KEY] = {}
        config[GLOBAL_PRODUCT_MAP_KEY][pid] = code

    existing = load_global_costs(config)
    if code not in existing:
        config = save_global_cost(config, code, product_name=product_name or "")
    elif product_name and not existing[code].get("product_name"):
        config[GLOBAL_COSTS_KEY][code]["product_name"] = str(product_name).strip()
    return config


def delete_global_product_mapping(config: Dict, product_id, style_id=None) -> Dict:
    pid = _normalize_product_id(product_id)
    sid = _normalize_style_id(style_id)
    if pid:
        config.get(GLOBAL_PRODUCT_MAP_KEY, {}).pop(pid, None)
    if pid and sid:
        config.get(GLOBAL_STYLE_MAP_KEY, {}).pop(_style_map_key(pid, sid), None)
    return config


def lookup_global_merchant_code(product_id, style_id=None, config: Optional[Dict] = None) -> str:
    cfg = config or load_cost_config()
    pid = _normalize_product_id(product_id)
    sid = _normalize_style_id(style_id)
    if sid:
        style_code = cfg.get(GLOBAL_STYLE_MAP_KEY, {}).get(_style_map_key(pid, sid))
        if style_code:
            return style_code
    return cfg.get(GLOBAL_PRODUCT_MAP_KEY, {}).get(pid, "")


# ---------- 从订单中提取/刷新商家编码 ----------


def extract_merchant_codes_from_orders(store_name: str) -> pd.DataFrame:
    dates = list_available_dates(store_name)
    codes = set()
    for d in dates:
        try:
            orders = load_daily_orders(store_name, d)
            if orders.empty:
                continue
            code_col = _find_merchant_code_column(orders)
            if not code_col:
                continue
            for _, r in orders.iterrows():
                code = _normalize_code(r.get(code_col))
                if code:
                    codes.add(code)
        except Exception:
            continue
    if not codes:
        return pd.DataFrame(columns=["merchant_code"])
    return pd.DataFrame(sorted(codes), columns=["merchant_code"])


def get_all_merchant_codes() -> pd.DataFrame:
    codes = set()
    for store in list_tmall_stores():
        df = extract_merchant_codes_from_orders(store)
        if not df.empty:
            codes.update(df["merchant_code"].astype(str).tolist())
    config = load_cost_config()
    codes.update(str(v) for v in load_global_product_mapping(config).values() if v)
    codes.update(str(v) for v in config.get(GLOBAL_STYLE_MAP_KEY, {}).values() if v)
    codes.update(str(k) for k in load_global_costs(config).keys() if k)
    if not codes:
        return pd.DataFrame(columns=["merchant_code"])
    return pd.DataFrame(sorted(codes), columns=["merchant_code"])


def refresh_global_cost_codes() -> Dict[str, int]:
    config = load_cost_config()
    existing = load_global_costs(config)
    detected = get_all_merchant_codes()
    added = 0
    for code in detected["merchant_code"].astype(str).tolist():
        code = _normalize_code(code)
        if not code or code in existing:
            continue
        config = save_global_cost(config, code)
        added += 1
    if added:
        save_cost_config(config)
    return {"added": added}


# ---------- 未映射商家编码的商品 ----------


def get_products_without_merchant_code(
    store_names: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    stores = store_names if store_names else list_tmall_stores()
    config = load_cost_config()
    rows = []
    for store in stores:
        dates = list_available_dates(store)
        if start_date and end_date:
            dates = [d for d in dates if start_date <= d <= end_date]
        for d in dates:
            try:
                orders = load_daily_orders(store, d)
                if orders.empty:
                    continue
                code_col = _find_merchant_code_column(orders)
                style_cols = _find_style_columns(orders)
                if "product_id" not in orders.columns:
                    continue
                for _, r in orders.iterrows():
                    pid = _normalize_product_id(r.get("product_id"))
                    pname = str(r.get("product_name", "") or "").strip()
                    sid = _normalize_style_id(r.get(style_cols.get("style_id_col") or "style_id"))
                    sname = str(
                        r.get(style_cols.get("style_name_col") or "style_name")
                        or r.get(style_cols.get("spec_col"))
                        or ""
                    ).strip()
                    if not pid:
                        continue
                    if code_col and _normalize_code(r.get(code_col)):
                        continue
                    if lookup_global_merchant_code(pid, sid, config):
                        continue
                    rows.append({
                        "product_id": pid,
                        "product_name": pname,
                        "style_id": sid or "-",
                        "style_name": sname or "-",
                        "store_name": store,
                        "date": d,
                    })
            except Exception:
                continue
    if not rows:
        return pd.DataFrame(columns=["product_id", "product_name", "style_id", "style_name", "store_name", "order_count", "first_date"])
    df = pd.DataFrame(rows)
    agg = df.groupby(["product_id", "product_name", "style_id", "style_name", "store_name"], as_index=False).agg(
        order_count=("date", "count"),
        first_date=("date", "min"),
    )
    return agg.sort_values(["order_count", "product_id"], ascending=[False, True])


# ---------- 导入/导出 ----------


def _normalize_cost_column_name(name: str) -> str:
    name = str(name).strip().replace(" ", "").replace("(元)", "").replace("（元）", "")
    mapping = {
        "商家编码": "merchant_code",
        "商家代码": "merchant_code",
        "商品编码": "merchant_code",
        "链接编码": "merchant_code",
        "merchantcode": "merchant_code",
        "merchant_code": "merchant_code",
        "商品名称": "product_name",
        "商品名": "product_name",
        "productname": "product_name",
        "product_name": "product_name",
        "商品成本": "product_cost",
        "商品成本/件": "product_cost",
        "成本": "product_cost",
        "productcost": "product_cost",
        "product_cost": "product_cost",
        "物流成本": "logistics_cost",
        "物流成本/件": "logistics_cost",
        "logisticscost": "logistics_cost",
        "logistics_cost": "logistics_cost",
    }
    return mapping.get(name, name)


def export_global_costs_to_csv(pending_only: bool = False) -> str:
    rows = list_global_cost_rows()
    if pending_only:
        rows = [r for r in rows if (r.get("product_cost") or 0) <= 0 or (r.get("logistics_cost") or 0) <= 0]
    df = pd.DataFrame(rows, columns=["merchant_code", "product_name", "product_cost", "logistics_cost"])
    df.columns = ["商家编码", "商品名称", "商品成本/件", "物流成本/件"]
    return df.to_csv(index=False, encoding="utf-8-sig")


def import_global_costs_from_csv(file_bytes: bytes) -> int:
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
        if norm in ["merchant_code", "product_name", "product_cost", "logistics_cost"]:
            rename[col] = norm
    df = df.rename(columns=rename)

    required = ["merchant_code", "product_cost", "logistics_cost"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"CSV 缺少必要列：{col}")

    cfg = load_cost_config()
    count = 0
    for _, rec in df.iterrows():
        code = _normalize_code(rec.get("merchant_code"))
        if not code:
            continue
        cfg = save_global_cost(
            cfg,
            merchant_code=code,
            product_name=str(rec.get("product_name", "") or ""),
            product_cost=pd.to_numeric(rec.get("product_cost", 0), errors="coerce") or 0,
            logistics_cost=pd.to_numeric(rec.get("logistics_cost", 0), errors="coerce") or 0,
        )
        count += 1
    if count:
        save_cost_config(cfg)
    return count


# ---------- 应用成本到指标表 ----------


def _load_old_product_costs(config: Dict) -> Dict[str, Dict[str, float]]:
    """兼容旧版按 product_id 存储的成本。"""
    products = config.get("products", {})
    return {
        _normalize_product_id(pid): {
            "product_cost": float(item.get("product_cost", 0) or 0),
            "logistics_cost": float(item.get("logistics_cost", 0) or 0),
        }
        for pid, item in products.items()
    }


def apply_costs_to_metrics(metrics: pd.DataFrame, store_name: Optional[str] = None) -> pd.DataFrame:
    if metrics is None or metrics.empty:
        return metrics

    df = metrics.copy()
    config = load_cost_config()
    global_costs = load_global_costs(config)
    cost_df = pd.DataFrame([{"merchant_code": code, **info} for code, info in global_costs.items()])

    # 确定/补齐 merchant_code
    if "merchant_code" in df.columns:
        df["merchant_code"] = (
            df["merchant_code"].astype(str).str.strip()
            .replace(["None", "nan", "NaN"], "")
            .fillna("")
        )
    else:
        df["merchant_code"] = ""

    if "product_id" in df.columns:
        style_id_col = None
        for col in df.columns:
            if str(col).lower() in ("style_id", "样式id", "款式id"):
                style_id_col = col
                break
        if style_id_col:
            df["merchant_code"] = df.apply(
                lambda r: lookup_global_merchant_code(r["product_id"], r.get(style_id_col), config) or r["merchant_code"],
                axis=1,
            )
        else:
            df["merchant_code"] = df.apply(
                lambda r: lookup_global_merchant_code(r["product_id"], None, config) or r["merchant_code"],
                axis=1,
            )

    df["merchant_code"] = df["merchant_code"].fillna("").astype(str).str.strip()

    if not cost_df.empty:
        df = df.merge(
            cost_df[["merchant_code", "product_cost", "logistics_cost"]],
            on="merchant_code",
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

    # 兜底：旧版按 product_id 的成本 + 全局映射未命中的商品直接按 product_id 查找
    old_costs = _load_old_product_costs(config)
    blank_mask = df["merchant_code"].replace("", pd.NA).isna()
    if blank_mask.any() and "product_id" in df.columns and old_costs:
        def _lookup_old(pid):
            item = old_costs.get(_normalize_product_id(pid), {})
            return item.get("product_cost", 0.0), item.get("logistics_cost", 0.0)
        mapped = df.loc[blank_mask, "product_id"].apply(_lookup_old)
        df.loc[blank_mask, "product_cost_unit"] = [x[0] for x in mapped]
        df.loc[blank_mask, "logistics_cost_unit"] = [x[1] for x in mapped]

    # 成本数量优先用「有效商品件数」，其次用「有效订单数」兜底
    if "valid_quantity" in df.columns:
        quantity = pd.to_numeric(df["valid_quantity"], errors="coerce").fillna(0)
    elif "quantity" in df.columns:
        quantity = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    else:
        quantity = pd.to_numeric(df.get("valid_order_count", 0), errors="coerce").fillna(0)
    income = pd.to_numeric(df.get("valid_gmv", 0), errors="coerce").fillna(0)
    spend = pd.to_numeric(df.get("spend", 0), errors="coerce").fillna(0)

    df["total_product_cost"] = df["product_cost_unit"] * quantity
    df["total_logistics_cost"] = df["logistics_cost_unit"] * quantity
    df["total_cost"] = df["total_product_cost"] + df["total_logistics_cost"]
    df["gross_profit"] = income - df["total_cost"]
    df["profit_loss"] = df["gross_profit"] - spend
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
