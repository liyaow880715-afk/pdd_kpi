"""
业务服务层：把 Streamlit 无关的核心逻辑封装成纯函数，供 FastAPI routers 调用。
"""

import io
import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from data_loader import read_promotion_file, read_order_file
from data_processor import match_promotion_and_orders
from metrics import (
    compute_product_metrics,
    compute_overall_kpis,
    aggregate_product_metrics,
    aggregate_style_metrics,
    merge_refund_stage_counts,
)
from cost_manager import (
    apply_costs_to_metrics,
    load_cost_config,
    save_cost_config,
    set_cost,
    append_new_merchant_codes,
    import_costs_from_csv,
    export_costs_to_csv,
    set_product_merchant_mapping,
    load_product_merchant_mapping,
    list_global_cost_rows,
    save_global_cost,
    load_global_costs,
    load_global_product_mapping,
    save_global_product_mapping,
    get_all_merchant_codes,
    get_products_without_merchant_code,
    refresh_global_cost_codes,
)
from storage import (
    save_daily_data,
    load_daily_data,
    load_daily_orders,
    list_available_stores,
    list_available_dates,
    list_store_records,
    record_exists,
    delete_daily_data,
)
from store_manager import add_store, rename_store, delete_store, list_stores
from config_manager import load_config, save_config, get_config_defaults
from ai_analyzer import generate_ai_report
from api_client import test_connection
from wecom import send_wecom_report, save_wecom_config, listen_wecom_chatid
from report_builder import build_daily_report


def _date_str(d) -> str:
    if isinstance(d, datetime.date):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%d")
    return str(d)


def _df_to_records(df: pd.DataFrame) -> List[Dict]:
    if df is None or df.empty:
        return []
    return df.replace({pd.NA: None, float("nan"): None}).to_dict("records")


# ---------- 店铺 ----------

def get_stores() -> List[Dict[str, Any]]:
    return list_stores()


def create_store(name: str) -> Dict[str, Any]:
    return add_store(name)


def rename_store_service(store_id: str, new_name: str) -> Optional[Dict[str, Any]]:
    return rename_store(store_id, new_name)


def delete_store_service(store_id: str) -> bool:
    return delete_store(store_id)


# ---------- 导入 ----------

def import_daily_data(
    store_name: str,
    import_date: datetime.date,
    promo_bytes: bytes,
    promo_filename: str,
    order_bytes: bytes,
    order_filename: str,
) -> Dict[str, Any]:
    promo_file = io.BytesIO(promo_bytes)
    promo_file.name = promo_filename
    order_file = io.BytesIO(order_bytes)
    order_file.name = order_filename

    promo_df, promo_mapping = read_promotion_file(promo_file)
    order_df, order_mapping = read_order_file(order_file)

    merged, style_metrics, orders = match_promotion_and_orders(
        promo_df,
        order_df,
        promo_mapping,
        order_mapping,
        date=_date_str(import_date),
    )
    merged["store_name"] = store_name
    style_metrics["store_name"] = store_name
    orders["store_name"] = store_name

    metrics = compute_product_metrics(merged)

    save_daily_data(
        metrics,
        style_metrics,
        orders,
        date=_date_str(import_date),
        store_name=store_name,
        meta={"promo_file": promo_filename, "order_file": order_filename},
    )
    return {
        "store_name": store_name,
        "date": _date_str(import_date),
        "product_rows": len(metrics),
        "style_rows": len(style_metrics),
        "order_rows": len(orders),
    }


# ---------- 订单 ----------

def get_orders(store_name: str, date: datetime.date) -> List[Dict[str, Any]]:
    try:
        df = load_daily_orders(_date_str(date), store_name)
    except FileNotFoundError:
        return []
    return _df_to_records(df)


def save_merchant_mapping(store_name: str, product_id: str, merchant_code: str) -> Dict[str, Any]:
    cfg = load_cost_config()
    cfg = set_product_merchant_mapping(cfg, store_name, product_id, merchant_code)
    costs = cfg.get("merchant_costs", {}).get(store_name, {})
    if merchant_code not in costs:
        cfg = set_cost(cfg, store_name=store_name, merchant_code=merchant_code)
    save_cost_config(cfg)
    return {"product_id": product_id, "merchant_code": merchant_code}


# ---------- 指标 ----------

def load_analysis_data(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    dates = list_available_dates(store_name)
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    selected_dates = [d for d in dates if start_s <= d <= end_s]

    if not selected_dates:
        return {"product_metrics": [], "style_metrics": [], "kpis": {}}

    product_dfs = []
    order_dfs = []
    for d in selected_dates:
        try:
            p, _ = load_daily_data(d, store_name)
            product_dfs.append(p)
        except Exception:
            continue
        try:
            orders = load_daily_orders(d, store_name)
            if not orders.empty:
                order_dfs.append(orders)
        except Exception:
            continue

    if not product_dfs:
        return {"product_metrics": [], "style_metrics": [], "kpis": {}}

    metrics = aggregate_product_metrics(product_dfs)
    metrics = merge_refund_stage_counts(metrics, order_dfs)
    metrics = compute_product_metrics(metrics)
    metrics = apply_costs_to_metrics(metrics, store_name)
    style_metrics = aggregate_style_metrics(order_dfs) if order_dfs else pd.DataFrame()
    kpis = compute_overall_kpis(metrics)

    # 把 float nan 转为 None，避免 JSON 序列化问题
    return {
        "product_metrics": _df_to_records(metrics),
        "style_metrics": _df_to_records(style_metrics),
        "kpis": {k: (None if pd.isna(v) else v) for k, v in kpis.items()},
    }


def load_trend_data(
    store_names: List[str],
    start_date: datetime.date,
    end_date: datetime.date,
) -> List[Dict[str, Any]]:
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    rows = []
    for store in store_names:
        dates = [d for d in list_available_dates(store) if start_s <= d <= end_s]
        for d in dates:
            try:
                p, _ = load_daily_data(d, store)
                p = apply_costs_to_metrics(p, store)
                day_kpis = compute_overall_kpis(p)
                rows.append({
                    "store_name": store,
                    "date": d,
                    "promo_spend": day_kpis.get("promo_spend", 0),
                    "promo_gmv": day_kpis.get("promo_gmv", 0),
                    "valid_order_gmv": day_kpis.get("valid_order_gmv", 0),
                    "valid_merchant_income": day_kpis.get("valid_merchant_income", 0),
                })
            except Exception:
                continue
    return rows


# ---------- 成本 ----------

def get_costs(store_name: str) -> List[Dict[str, Any]]:
    cfg = load_cost_config()
    costs = cfg.get("merchant_costs", {}).get(store_name, {})
    rows = []
    for code, info in costs.items():
        rows.append({
            "merchant_code": code,
            "product_name": info.get("product_name", ""),
            "product_cost": float(info.get("product_cost", 0) or 0),
            "logistics_cost": float(info.get("logistics_cost", 0) or 0),
        })
    return rows


def save_costs(store_name: str, costs: List[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = load_cost_config()
    for rec in costs:
        code = str(rec.get("merchant_code", "")).strip()
        if not code:
            continue
        cfg = set_cost(
            cfg,
            store_name=store_name,
            merchant_code=code,
            product_name=rec.get("product_name", ""),
            product_cost=rec.get("product_cost", 0),
            logistics_cost=rec.get("logistics_cost", 0),
        )
    save_cost_config(cfg)
    return {"saved": len(costs)}


def refresh_cost_codes(store_name: str) -> Dict[str, Any]:
    added = append_new_merchant_codes(store_name)
    return {"added": added}


def export_cost_csv(store_name: str) -> str:
    return export_costs_to_csv(store_name)


def import_cost_csv(store_name: str, file_bytes: bytes) -> Dict[str, Any]:
    file_obj = io.BytesIO(file_bytes)
    count = import_costs_from_csv(store_name, file_obj)
    return {"updated": count}


# ---------- 全局成本（不区分店铺） ----------

def get_global_costs() -> List[Dict[str, Any]]:
    cfg = load_cost_config()
    mapping = load_global_product_mapping(cfg)
    # 尝试给商品名称为空的成本记录补全名称
    code_to_name: Dict[str, str] = {}
    for pid, code in mapping.items():
        if code not in code_to_name:
            code_to_name[code] = ""
    # 从订单中查找商品名称
    from storage import list_available_stores, list_available_dates, load_daily_orders
    for store in list_available_stores() or []:
        for d in list_available_dates(store):
            try:
                orders = load_daily_orders(d, store)
                if orders.empty or "product_id" not in orders.columns:
                    continue
                for _, r in orders.iterrows():
                    pid = str(r.get("product_id") or "").strip()
                    if pid.endswith(".0"):
                        pid = pid[:-2]
                    code = mapping.get(pid)
                    if code and not code_to_name.get(code):
                        pname = str(r.get("product_name") or "").strip()
                        if pname:
                            code_to_name[code] = pname
            except Exception:
                continue

    rows = []
    for rec in list_global_cost_rows(cfg):
        pname = rec.get("product_name", "")
        if not pname:
            pname = code_to_name.get(rec["merchant_code"], "")
            if pname:
                cfg["global_merchant_costs"][rec["merchant_code"]]["product_name"] = pname
        rows.append({
            "merchant_code": rec["merchant_code"],
            "product_name": pname,
            "product_cost": float(rec.get("product_cost", 0) or 0),
            "logistics_cost": float(rec.get("logistics_cost", 0) or 0),
        })
    if code_to_name:
        save_cost_config(cfg)
    return rows


def save_global_costs(costs: List[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = load_cost_config()
    for rec in costs:
        code = str(rec.get("merchant_code", "")).strip()
        if not code:
            continue
        cfg = save_global_cost(
            cfg,
            merchant_code=code,
            product_name=rec.get("product_name", ""),
            product_cost=rec.get("product_cost", 0),
            logistics_cost=rec.get("logistics_cost", 0),
        )
    save_cost_config(cfg)
    return {"saved": len(costs)}


def refresh_global_cost_codes_service() -> Dict[str, Any]:
    return refresh_global_cost_codes()


def get_unmapped_products() -> List[Dict[str, Any]]:
    df = get_products_without_merchant_code()
    return _df_to_records(df)


def save_global_product_mapping_service(
    product_id: str,
    merchant_code: str,
    style_id: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = load_cost_config()
    cfg = save_global_product_mapping(cfg, product_id, merchant_code, style_id=style_id, product_name=product_name or "")
    save_cost_config(cfg)
    return {"product_id": product_id, "style_id": style_id, "merchant_code": merchant_code}


# ---------- AI ----------

def get_ai_config() -> Dict[str, Any]:
    return get_config_defaults()


def update_ai_config(config: Dict[str, Any]) -> Dict[str, Any]:
    save_config(config)
    return config


def test_ai_service(config: Dict[str, Any]) -> Dict[str, Any]:
    return test_connection(
        config.get("api_key", ""),
        config.get("base_url", "https://api.kimi.com/coding/v1"),
        config.get("model", "kimi-coding"),
        timeout=30,
    )


def generate_ai_report_service(
    store_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    data = load_analysis_data(store_name, start_date, end_date)
    kpis = data["kpis"]
    metrics = pd.DataFrame(data["product_metrics"])
    if metrics.empty or not kpis:
        raise ValueError("指定日期范围内没有数据")
    return generate_ai_report(
        kpis=kpis,
        metrics=metrics,
        api_key=config.get("api_key") or None,
        base_url=config.get("base_url", "https://api.kimi.com/coding/v1"),
        model=config.get("model", "kimi-coding"),
        temperature=config.get("temperature", 1.0),
        reasoning_effort=config.get("reasoning_effort", "low"),
        timeout=config.get("timeout", 60),
        max_completion_tokens=config.get("max_completion_tokens", 16384),
        date=f"{_date_str(start_date)} ~ {_date_str(end_date)}",
    )


# ---------- 企业微信 ----------

def get_wecom_config() -> Dict[str, Any]:
    from wecom import load_wecom_config
    return load_wecom_config()


def update_wecom_config(config: Dict[str, Any]) -> Dict[str, Any]:
    save_wecom_config(config)
    return config


def listen_wecom(config: Dict[str, Any], timeout: int = 60) -> Optional[str]:
    return listen_wecom_chatid(
        config.get("bot_id", ""),
        config.get("secret", ""),
        timeout=timeout,
    )


def send_wecom_report_service(report_date: datetime.date, config: Dict[str, Any]) -> Dict[str, Any]:
    content = build_daily_report(_date_str(report_date))
    result = send_wecom_report(content, config)
    return result


# ---------- 导出 ----------

def export_product_metrics_csv(store_name: str, start_date: datetime.date, end_date: datetime.date) -> str:
    data = load_analysis_data(store_name, start_date, end_date)
    df = pd.DataFrame(data["product_metrics"])
    return df.to_csv(index=False, encoding="utf-8-sig")


def export_style_metrics_csv(store_name: str, start_date: datetime.date, end_date: datetime.date) -> str:
    data = load_analysis_data(store_name, start_date, end_date)
    df = pd.DataFrame(data["style_metrics"])
    return df.to_csv(index=False, encoding="utf-8-sig")


# ---------- 历史记录 ----------

def get_records(store_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_store_records(store_name)


def delete_record(store_name: str, date: datetime.date) -> Dict[str, Any]:
    delete_daily_data(store_name, _date_str(date))
    return {"deleted": True, "store_name": store_name, "date": _date_str(date)}
