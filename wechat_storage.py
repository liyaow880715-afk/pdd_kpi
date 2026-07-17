"""
微信小店数据存储
- 店铺数据存放到 data/processed_wechat/{store_safe}/
- 每日保存：商品指标、订单
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

DATA_DIR = Path("data/processed_wechat")


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _store_dir(store_name: str) -> Path:
    safe = str(store_name).strip().replace("/", "_").replace("\\", "_").replace(" ", "_") or "default"
    return DATA_DIR / safe


def list_wechat_stores() -> List[str]:
    _ensure_dir()
    stores = []
    for d in DATA_DIR.iterdir():
        if d.is_dir():
            stores.append(d.name)
    return sorted(stores)


def list_available_dates(store_name: str) -> List[str]:
    d = _store_dir(store_name)
    if not d.exists():
        return []
    dates = set()
    for f in d.glob("*.parquet"):
        if "_" in f.stem:
            dates.add(f.stem.split("_")[0])
    return sorted(dates)


def save_daily_data(
    store_name: str,
    date: str,
    product_metrics: pd.DataFrame,
    orders: Optional[pd.DataFrame] = None,
    meta: Optional[Dict] = None,
):
    d = _store_dir(store_name)
    d.mkdir(parents=True, exist_ok=True)
    product_metrics.to_parquet(d / f"{date}_product.parquet", index=False)
    if orders is not None:
        orders.to_parquet(d / f"{date}_orders.parquet", index=False)
    if meta:
        (d / f"{date}_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def load_daily_data(store_name: str, date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    d = _store_dir(store_name)
    product_path = d / f"{date}_product.parquet"
    order_path = d / f"{date}_orders.parquet"
    product = pd.read_parquet(product_path) if product_path.exists() else pd.DataFrame()
    orders = pd.read_parquet(order_path) if order_path.exists() else pd.DataFrame()
    return product, orders


def load_daily_orders(store_name: str, date: str) -> pd.DataFrame:
    d = _store_dir(store_name)
    order_path = d / f"{date}_orders.parquet"
    return pd.read_parquet(order_path) if order_path.exists() else pd.DataFrame()


def delete_daily_data(store_name: str, date: str):
    d = _store_dir(store_name)
    for suffix in ["product", "orders"]:
        for ext in ["parquet", "csv"]:
            f = d / f"{date}_{suffix}.{ext}"
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
    meta_path = d / f"{date}_meta.json"
    if meta_path.exists():
        try:
            meta_path.unlink()
        except Exception:
            pass


def list_wechat_records(store_name: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_dir()
    records = []
    stores = [_store_dir(store_name)] if store_name else [d for d in DATA_DIR.iterdir() if d.is_dir()]
    for d in stores:
        store = d.name
        dates = set()
        for f in d.glob("*_meta.json"):
            if "_" in f.stem:
                dates.add(f.stem.split("_")[0])
        for f in d.glob("*_product.parquet"):
            if "_" in f.stem:
                dates.add(f.stem.split("_")[0])
        for date in sorted(dates):
            meta_path = d / f"{date}_meta.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            meta.setdefault("date", date)
            meta.setdefault("store_name", store)
            if "product_rows" not in meta:
                product_path = d / f"{date}_product.parquet"
                try:
                    df = pd.read_parquet(product_path)
                    meta["product_rows"] = len(df)
                except Exception:
                    meta["product_rows"] = 0
            if "order_rows" not in meta:
                order_path = d / f"{date}_orders.parquet"
                try:
                    df = pd.read_parquet(order_path)
                    meta["order_rows"] = len(df)
                except Exception:
                    meta["order_rows"] = 0
            records.append(meta)
    return sorted(records, key=lambda x: (x.get("store_name", ""), x.get("date", "")))
