"""
通用日报生成器
- 供抖音、天猫等口径相近的平台复用
- 拼多多因指标口径差异仍使用 report_builder.py
"""

import datetime
from typing import Any, Callable, Dict, List


def _safe_num(v: Any) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _date_str(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


def build_daily_report(
    report_date: datetime.date,
    title: str,
    list_stores: Callable[[], List[str]],
    load_analysis: Callable[[str, datetime.date, datetime.date], Dict[str, Any]],
) -> str:
    """基于店铺分析数据构建 Markdown 日报"""
    date_str = _date_str(report_date)
    stores = list_stores()

    lines = [f"# {title} {date_str}", ""]

    if not stores:
        lines.append("暂无店铺数据。")
        return "\n".join(lines)

    total_spend = 0.0
    total_gmv = 0.0
    total_valid_gmv = 0.0
    total_orders = 0.0
    total_valid_orders = 0.0
    total_cost = 0.0
    total_profit = 0.0

    for store in stores:
        try:
            analysis = load_analysis(store, report_date, report_date)
            kpis = analysis.get("kpis") or {}
            cost_kpis = analysis.get("cost_kpis") or {}

            spend = _safe_num(kpis.get("spend"))
            gmv = _safe_num(kpis.get("gmv"))
            valid_gmv = _safe_num(kpis.get("valid_gmv"))
            orders = _safe_num(kpis.get("order_count"))
            valid_orders = _safe_num(kpis.get("valid_order_count"))
            roi = _safe_num(kpis.get("roi"))
            ctr = _safe_num(kpis.get("ctr"))
            cvr = _safe_num(kpis.get("cvr"))
            refund_rate = _safe_num(kpis.get("refund_rate"))
            cost = _safe_num(cost_kpis.get("total_cost"))
            profit = _safe_num(cost_kpis.get("profit_loss"))

            total_spend += spend
            total_gmv += gmv
            total_valid_gmv += valid_gmv
            total_orders += orders
            total_valid_orders += valid_orders
            total_cost += cost
            total_profit += profit

            lines.append(f"## {store}")
            lines.append(f"- 消耗：{spend:.2f}，成交：{gmv:.2f}，净成交：{valid_gmv:.2f}")
            lines.append(f"- 订单：{orders:.0f}，净订单：{valid_orders:.0f}，ROI：{roi:.2f}")
            lines.append(f"- 点击率：{ctr:.2f}%，转化率：{cvr:.2f}%，退款率：{refund_rate:.2f}%")
            lines.append(f"- 成本：{cost:.2f}，盈亏：{profit:.2f}")
            lines.append("")
        except Exception:
            lines.append(f"## {store}")
            lines.append("数据加载失败。")
            lines.append("")

    total_roi = total_gmv / total_spend if total_spend else 0.0
    lines.append("## 合计")
    lines.append(f"- 消耗：{total_spend:.2f}，成交：{total_gmv:.2f}，净成交：{total_valid_gmv:.2f}")
    lines.append(f"- 订单：{total_orders:.0f}，净订单：{total_valid_orders:.0f}，综合 ROI：{total_roi:.2f}")
    lines.append(f"- 总成本：{total_cost:.2f}，总盈亏：{total_profit:.2f}")

    return "\n".join(lines)
