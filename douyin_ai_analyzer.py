"""
抖音 AI 分析器
- 基于抖音指标生成 AI 分析报告
- 独立于拼多多的 ai_analyzer.py
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from api_client import call_llm
from config_manager import load_config, save_config

CONFIG_KEY = "ai_config_douyin"


def get_ai_config() -> Dict[str, Any]:
    config = load_config()
    defaults = {
        "base_url": "https://api.kimi.com/coding/v1",
        "model": "kimi-coding",
        "temperature": 1.0,
        "reasoning_effort": "low",
        "api_key": "",
        "timeout": 60,
        "max_completion_tokens": 16384,
    }
    defaults.update(config.get(CONFIG_KEY, {}))
    return defaults


def update_ai_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config()
    current = config.get(CONFIG_KEY, {})
    current.update(updates)
    config[CONFIG_KEY] = current
    save_config(config)
    return current


def test_ai_connection(config: Dict[str, Any]) -> str:
    prompt = "你好，请用一句话证明你能正常回复。"
    return call_llm(
        prompt=prompt,
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", "https://api.kimi.com/coding/v1"),
        model=config.get("model", "kimi-coding"),
        temperature=float(config.get("temperature", 1.0)),
        reasoning_effort=config.get("reasoning_effort", "low"),
        system_prompt="你是一位资深的抖音电商投放分析师。",
        timeout=int(config.get("timeout", 60)),
        max_completion_tokens=int(config.get("max_completion_tokens", 16384)),
    )


def _safe_num(v: Any) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def build_prompt(kpis: Dict[str, Any], product_metrics: List[Dict[str, Any]]) -> str:
    top_products = sorted(
        product_metrics,
        key=lambda x: _safe_num(x.get("spend")),
        reverse=True,
    )[:10]

    product_lines = []
    for p in top_products:
        product_lines.append(
            f"- {p.get('product_name') or p.get('product_id')}: 消耗 {_safe_num(p.get('spend')):.2f}, "
            f"GMV {_safe_num(p.get('gmv')):.2f}, 净GMV {_safe_num(p.get('valid_gmv')):.2f}, "
            f"ROI {_safe_num(p.get('roi')):.2f}, 点击率 {_safe_num(p.get('ctr')):.2f}%, "
            f"转化率 {_safe_num(p.get('cvr')):.2f}%, 退款率 {_safe_num(p.get('refund_rate')):.2f}%"
        )

    prompt = f"""你是一位资深抖音电商投放分析师。请根据以下数据出具一份简明的中文分析报告，包括：
1. 整体表现总结（消耗、成交、ROI、点击率、转化率、退款率）。
2. 成本与利润情况（总成本、毛利润、盈亏、毛利率、盈亏率）。
3.  top 商品表现点评。
4. 给出 3-5 条可执行的优化建议。

整体指标：
- 消耗：{_safe_num(kpis.get('spend')):.2f}
- 成交金额：{_safe_num(kpis.get('gmv')):.2f}
- 净成交金额：{_safe_num(kpis.get('valid_gmv')):.2f}
- 订单数：{_safe_num(kpis.get('order_count')):.0f}
- 净订单数：{_safe_num(kpis.get('valid_order_count')):.0f}
- ROI：{_safe_num(kpis.get('roi')):.2f}
- 有效 ROI：{_safe_num(kpis.get('valid_roi')):.2f}
- 点击率：{_safe_num(kpis.get('ctr')):.2f}%
- 转化率：{_safe_num(kpis.get('cvr')):.2f}%
- CPC：{_safe_num(kpis.get('cpc')):.2f}
- CPM：{_safe_num(kpis.get('cpm')):.2f}
- 退款率：{_safe_num(kpis.get('refund_rate')):.2f}%
- 总成本：{_safe_num(kpis.get('total_cost')):.2f}
- 毛利润：{_safe_num(kpis.get('gross_profit')):.2f}
- 盈亏：{_safe_num(kpis.get('profit_loss')):.2f}
- 毛利率：{_safe_num(kpis.get('gross_margin_rate')):.2f}%
- 盈亏率：{_safe_num(kpis.get('profit_loss_rate')):.2f}%

TOP 商品（按消耗排序）：
{chr(10).join(product_lines) if product_lines else '暂无商品数据'}
"""
    return prompt


def generate_ai_report(
    kpis: Dict[str, Any],
    product_metrics: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if config is None:
        config = get_ai_config()

    prompt = build_prompt(kpis, product_metrics)

    try:
        content = call_llm(
            prompt=prompt,
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.kimi.com/coding/v1"),
            model=config.get("model", "kimi-coding"),
            temperature=float(config.get("temperature", 1.0)),
            reasoning_effort=config.get("reasoning_effort", "low"),
            system_prompt="你是一位资深的抖音电商投放分析师，擅长用数据驱动决策。",
            timeout=int(config.get("timeout", 60)),
            max_completion_tokens=int(config.get("max_completion_tokens", 16384)),
        )
        return {"report": content}
    except Exception as e:
        return {"report": f"", "error": str(e)}
