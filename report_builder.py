"""
企业微信汇总报告生成器
"""

import datetime
from typing import Dict, List, Optional

import pandas as pd

from storage import list_available_stores, list_available_dates, load_daily_data
from metrics import compute_overall_kpis, aggregate_product_metrics


def _date_str(d) -> str:
    if isinstance(d, datetime.date):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%d")
    return str(d)


def _load_store_metrics_for_range(store_name: str, start_date, end_date) -> Optional[pd.DataFrame]:
    """加载店铺在日期范围内的汇总商品指标"""
    dates = list_available_dates(store_name)
    start_s = _date_str(start_date)
    end_s = _date_str(end_date)
    selected = [d for d in dates if start_s <= d <= end_s]
    if not selected:
        return None

    dfs = []
    for d in selected:
        try:
            df, _ = load_daily_data(d, store_name)
            dfs.append(df)
        except Exception:
            continue
    if not dfs:
        return None
    return aggregate_product_metrics(dfs)


def _build_store_summary(store_name: str, report_date: datetime.date) -> Optional[Dict]:
    """构建单个店铺昨日 + 本月累计摘要"""
    yesterday = report_date - datetime.timedelta(days=1)
    month_start = yesterday.replace(day=1)

    # 昨日
    yesterday_metrics = _load_store_metrics_for_range(store_name, yesterday, yesterday)
    if yesterday_metrics is None:
        return None
    yesterday_kpis = compute_overall_kpis(yesterday_metrics)

    # 本月累计（1号到昨天）
    month_metrics = _load_store_metrics_for_range(store_name, month_start, yesterday)
    month_kpis = compute_overall_kpis(month_metrics) if month_metrics is not None else {}

    return {
        "store_name": store_name,
        "yesterday": yesterday,
        "month_start": month_start,
        "yesterday_kpis": yesterday_kpis,
        "month_kpis": month_kpis,
    }


def _format_money(value: float) -> str:
    return f"{value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value:.2f}%"


def build_daily_report(report_date: datetime.date = None) -> str:
    """
    构建所有店铺昨日销售汇总报告（Markdown 格式）
    """
    if report_date is None:
        report_date = datetime.date.today()

    yesterday = report_date - datetime.timedelta(days=1)
    stores = list_available_stores()

    lines = []
    lines.append(f"## 📊 拼多多推广日报 ({yesterday.strftime('%Y-%m-%d')})")
    lines.append("")
    lines.append(f"> 统计范围：昨日 {yesterday.strftime('%Y-%m-%d')} + 本月累计 {yesterday.replace(day=1).strftime('%Y-%m-%d')} ~ {yesterday.strftime('%Y-%m-%d')}")
    lines.append("")

    has_data = False
    for store in stores:
        summary = _build_store_summary(store, report_date)
        if summary is None:
            continue
        has_data = True
        y = summary["yesterday_kpis"]
        m = summary["month_kpis"]

        roi_status = "🟢" if y.get("real_roi", 0) >= 2.5 else ("🟡" if y.get("real_roi", 0) >= 1.5 else "🔴")
        problem_status = "🟢" if y.get("problem_rate", 0) < 20 else "🔴"

        lines.append(f"### {store}")
        lines.append("")
        lines.append("**昨日数据**")
        lines.append(f"- 推广花费：¥{_format_money(y.get('promo_spend', 0))}")
        lines.append(f"- 推广 GMV：¥{_format_money(y.get('promo_gmv', 0))}")
        lines.append(f"- 有效商家实收：¥{_format_money(y.get('valid_merchant_income', 0))}")
        lines.append(f"- 真实 ROI：{y.get('real_roi', 0):.2f} {roi_status}")
        lines.append(f"- 退款+取消率：{_format_percent(y.get('problem_rate', 0))} {problem_status}")
        lines.append("")

        if m:
            lines.append("**本月累计**")
            lines.append(f"- 推广花费：¥{_format_money(m.get('promo_spend', 0))}")
            lines.append(f"- 推广 GMV：¥{_format_money(m.get('promo_gmv', 0))}")
            lines.append(f"- 有效商家实收：¥{_format_money(m.get('valid_merchant_income', 0))}")
            lines.append(f"- 真实 ROI：{m.get('real_roi', 0):.2f}")
            lines.append(f"- 订单数：{m.get('order_count', 0):.0f}")
            lines.append("")

    if not has_data:
        lines.append("暂无店铺数据，请先导入数据。")

    lines.append("---")
    lines.append("来自 拼多多推广 BI 看板")
    return "\n".join(lines)


def preview_report(report_date: datetime.date = None) -> str:
    """预览报告内容"""
    return build_daily_report(report_date)
