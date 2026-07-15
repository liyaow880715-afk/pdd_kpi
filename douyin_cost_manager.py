"""
抖音成本管理
- 独立于拼多多成本体系
- 存储文件：data/douyin_costs.json
- 成本按 product_id 维护（商品成本/件、物流成本/件）
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

COSTS_FILE = Path("data/douyin_costs.json")


def _ensure_dir():
    COSTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _normalize_id(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _load_raw() -> dict:
    if not COSTS_FILE.exists():
        return {"products": {}}
    try:
        return json.loads(COSTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"products": {}}


def _save_raw(data: dict):
    _ensure_dir()
    data["updated_at"] = datetime.now().isoformat()
    COSTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_costs() -> List[Dict[str, Any]]:
    """返回所有抖音商品成本列表"""
    raw = _load_raw()
    rows = []
    for product_id, item in raw.get("products", {}).items():
        rows.append({
            "product_id": _normalize_id(product_id),
            "product_name": item.get("product_name", ""),
            "product_cost": float(item.get("product_cost", 0) or 0),
            "logistics_cost": float(item.get("logistics_cost", 0) or 0),
            "updated_at": item.get("updated_at", ""),
        })
    return sorted(rows, key=lambda x: x["product_id"])


def save_costs(costs: List[Dict[str, Any]]):
    """批量保存抖音商品成本"""
    raw = _load_raw()
    products = raw.setdefault("products", {})
    now = datetime.now().isoformat()
    for row in costs:
        pid = _normalize_id(row.get("product_id"))
        if not pid:
            continue
        products[pid] = {
            "product_name": str(row.get("product_name", "")).strip(),
            "product_cost": float(row.get("product_cost", 0) or 0),
            "logistics_cost": float(row.get("logistics_cost", 0) or 0),
            "updated_at": now,
        }
    _save_raw(raw)


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def apply_costs_to_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """把成本应用到抖音商品指标表，添加成本相关列"""
    if metrics is None or metrics.empty:
        return metrics

    df = metrics.copy()
    costs = {r["product_id"]: r for r in get_costs()}

    df["product_cost_unit"] = df["product_id"].map(lambda x: costs.get(_normalize_id(x), {}).get("product_cost", 0.0)).fillna(0.0).astype(float)
    df["logistics_cost_unit"] = df["product_id"].map(lambda x: costs.get(_normalize_id(x), {}).get("logistics_cost", 0.0)).fillna(0.0).astype(float)

    # 抖音指标使用 valid_order_count 作为成本数量，valid_gmv 作为收入
    quantity = pd.to_numeric(df.get("valid_order_count", 0), errors="coerce").fillna(0)
    income = pd.to_numeric(df.get("valid_gmv", 0), errors="coerce").fillna(0)
    spend = pd.to_numeric(df.get("spend", 0), errors="coerce").fillna(0)

    df["total_product_cost"] = df["product_cost_unit"] * quantity
    df["total_logistics_cost"] = df["logistics_cost_unit"] * quantity
    df["total_cost"] = df["total_product_cost"] + df["total_logistics_cost"]
    df["gross_profit"] = income - df["total_cost"]
    df["profit_loss"] = df["gross_profit"] - spend
    df["gross_margin_rate"] = df.apply(lambda r: _safe_div(r["gross_profit"], r["valid_gmv"]) * 100, axis=1)
    df["profit_loss_rate"] = df.apply(lambda r: _safe_div(r["profit_loss"], r["valid_gmv"]) * 100, axis=1)

    return df


def compute_cost_kpis(metrics: pd.DataFrame) -> Dict[str, float]:
    """从已应用成本的指标表中汇总成本 KPI"""
    if metrics is None or metrics.empty:
        return {
            "total_cost": 0.0,
            "gross_profit": 0.0,
            "profit_loss": 0.0,
            "gross_margin_rate": 0.0,
            "profit_loss_rate": 0.0,
        }

    total_cost = float(metrics["total_cost"].sum())
    gross_profit = float(metrics["gross_profit"].sum())
    profit_loss = float(metrics["profit_loss"].sum())
    valid_gmv = float(pd.to_numeric(metrics.get("valid_gmv", 0), errors="coerce").fillna(0).sum())

    return {
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "profit_loss": profit_loss,
        "gross_margin_rate": _safe_div(gross_profit, valid_gmv) * 100,
        "profit_loss_rate": _safe_div(profit_loss, valid_gmv) * 100,
    }


def get_unmapped_products(metrics: pd.DataFrame) -> List[Dict[str, Any]]:
    """返回指标表中没有维护成本的商品列表"""
    if metrics is None or metrics.empty:
        return []
    costs = {r["product_id"] for r in get_costs()}
    rows = []
    seen = set()
    for _, r in metrics.iterrows():
        pid = _normalize_id(r.get("product_id"))
        if not pid or pid in costs or pid in seen:
            continue
        seen.add(pid)
        rows.append({
            "product_id": pid,
            "product_name": r.get("product_name", ""),
        })
    return rows


def export_costs_to_csv() -> bytes:
    """导出成本配置为 CSV 字节"""
    rows = get_costs()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["商品ID", "商品名称", "商品成本", "物流成本"])
    for r in rows:
        writer.writerow([r["product_id"], r["product_name"], r["product_cost"], r["logistics_cost"]])
    return output.getvalue().encode("utf-8-sig")


def import_costs_from_csv(file_bytes: bytes) -> Dict[str, Any]:
    """从 CSV 导入成本配置"""
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError("无法解析 CSV 编码")

    # 列名兼容
    col_map = {
        "product_id": ["商品ID", "商品id", "product_id", "商品编号"],
        "product_name": ["商品名称", "product_name"],
        "product_cost": ["商品成本", "商品成本/件", "成本", "product_cost"],
        "logistics_cost": ["物流成本", "物流成本/件", "logistics_cost"],
    }
    rename = {}
    for target, candidates in col_map.items():
        for c in df.columns:
            if c.strip() in candidates:
                rename[c] = target
                break
    df = df.rename(columns=rename)
    required = {"product_id", "product_cost", "logistics_cost"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列：{missing}")

    costs = []
    for _, r in df.iterrows():
        pid = _normalize_id(r.get("product_id"))
        if not pid:
            continue
        costs.append({
            "product_id": pid,
            "product_name": str(r.get("product_name", "")).strip(),
            "product_cost": float(r.get("product_cost", 0) or 0),
            "logistics_cost": float(r.get("logistics_cost", 0) or 0),
        })

    save_costs(costs)
    return {"updated": len(costs)}
