"""
AI 分析模块：生成提示词并调用 LLM，同时提供无 API 时的规则化洞察降级
"""

import json
import pandas as pd
from typing import Dict, List, Optional

from api_client import call_llm, test_connection


def build_prompt(kpis: Dict, metrics: pd.DataFrame, date: Optional[str] = None) -> str:
    """构建发送给 LLM 的提示词"""
    date_str = date or "今日"

    # 选择关键列用于上下文（优先使用有效/去退款后的指标）
    cols = [
        "product_name", "promo_spend", "promo_gmv", "promo_orders", "promo_roi",
        "order_count", "valid_order_count", "order_gmv", "valid_order_gmv",
        "merchant_income", "valid_merchant_income",
        "real_roi_merchant_income", "valid_order_gmv_roi",
        "refund_rate", "cancel_rate", "problem_rate",
        "organic_ratio_gmv", "ctr", "click_to_order_rate"
    ]
    cols = [c for c in cols if c in metrics.columns]
    df_context = metrics[cols].copy()

    # 排序：按花费降序
    df_context = df_context.sort_values("promo_spend", ascending=False)

    prompt = f"""你是一位资深的拼多多广告投放分析师。请根据以下 {date_str} 的推广与订单数据，给出专业的分析结论和可执行建议。

## 关键定义
- "有效" = 已剔除退款和取消订单后的数据
- 真实 ROI = 有效商家实收 / 推广花费
- 有效 GMV ROI = 有效订单 GMV / 推广花费

## 整体数据
- 推广总花费：{kpis['promo_spend']:.2f} 元
- 推广 GMV：{kpis['promo_gmv']:.2f} 元
- 订单总 GMV：{kpis['order_gmv']:.2f} 元
- 有效订单 GMV：{kpis.get('valid_order_gmv', 0):.2f} 元
- 商家实收合计：{kpis['merchant_income']:.2f} 元
- 有效商家实收：{kpis.get('valid_merchant_income', 0):.2f} 元
- 推广 ROI（GMV/花费）：{kpis['promo_roi']:.2f}
- 真实 ROI（有效实收/花费）：{kpis['real_roi']:.2f}
- 有效 GMV ROI：{kpis.get('valid_order_gmv_roi', 0):.2f}
- 订单总数：{kpis['order_count']:.0f} 笔
- 有效订单数：{kpis.get('valid_order_count', 0):.0f} 笔
- 推广成交笔数：{kpis['promo_orders']:.0f} 笔
- 退款率：{kpis['refund_rate']:.2f}%
- 取消率：{kpis['cancel_rate']:.2f}%
- 退款+取消率：{kpis['problem_rate']:.2f}%
- 自然流量 GMV 占比：{kpis['organic_ratio_gmv']:.2f}%
- 点击率 CTR：{kpis['ctr']:.2f}%
- 点击转化率：{kpis['click_to_order_rate']:.2f}%

## 商品明细
{df_context.to_string(index=False)}

请按以下结构输出（必须包含全部 7 个部分，每个部分用 ### 标题）：

### 1. 今日核心结论
用 3-5 句话总结今日投放表现，必须引用推广 ROI、真实 ROI、退款率等关键数据。

### 2. TOP3 盈利/高效商品
列出花费>0 且真实 ROI 最高的 3 个商品，说明原因。

### 3. TOP3 亏损/低效商品
列出花费>0 且真实 ROI 最低的 3 个商品，给出具体优化建议。

### 4. 退款/售后风险提示
指出退款率或取消率偏高的商品及风险等级。

### 5. 出价/预算/计划调整建议
针对每个低效商品给出：是否降出价、是否减预算、是否暂停。

### 6. 是否关停推广计划
明确回答哪些商品建议关停，为什么。

### 7. 明日可执行的 3 条行动项
给出 3 条最具体、可落地的行动建议。

要求：
- 结论要具体，必须引用数据
- 建议要可执行，不要泛泛而谈
- 如果某商品真实 ROI 低于 1.5 或退款率超过 20%，明确指出并建议处理
- 如果某商品有花费但无成交，必须建议暂停
"""
    return prompt


def rule_based_insights(kpis: Dict, metrics: pd.DataFrame) -> str:
    """当没有 API Key 或 API 失败时，使用规则化洞察"""
    lines = []
    lines.append("## 规则化智能洞察\n")

    # 整体结论
    if kpis["real_roi"] >= 2.5:
        lines.append(f"✅ 整体真实 ROI 为 {kpis['real_roi']:.2f}，投放效果良好，商家实收覆盖推广成本。")
    elif kpis["real_roi"] >= 1.5:
        lines.append(f"⚠️ 整体真实 ROI 为 {kpis['real_roi']:.2f}，处于盈亏边缘，建议优化低效计划。")
    else:
        lines.append(f"🚨 整体真实 ROI 仅 {kpis['real_roi']:.2f}，投放亏损，需立即排查。")

    if kpis["problem_rate"] > 20:
        lines.append(f"🚨 退款+取消率高达 {kpis['problem_rate']:.2f}%，售后风险较大，需关注商品质量/描述/物流。")
    elif kpis["problem_rate"] > 10:
        lines.append(f"⚠️ 退款+取消率为 {kpis['problem_rate']:.2f}%，略高于正常水平。")

    # TOP 高效
    top = metrics[metrics["promo_spend"] > 0].sort_values("real_roi_merchant_income", ascending=False).head(3)
    if not top.empty:
        lines.append("\n### TOP3 高效商品")
        for _, row in top.iterrows():
            lines.append(
                f"- **{row['product_name']}**：真实 ROI {row['real_roi_merchant_income']:.2f}，"
                f"花费 {row['promo_spend']:.2f} 元，商家实收 {row['merchant_income']:.2f} 元"
            )

    # TOP 低效
    bottom = metrics[metrics["promo_spend"] > 0].sort_values("real_roi_merchant_income", ascending=True).head(3)
    if not bottom.empty:
        lines.append("\n### TOP3 低效商品")
        for _, row in bottom.iterrows():
            lines.append(
                f"- **{row['product_name']}**：真实 ROI {row['real_roi_merchant_income']:.2f}，"
                f"花费 {row['promo_spend']:.2f} 元，商家实收 {row['merchant_income']:.2f} 元"
            )

    # 有花费无成交
    zero_sales = metrics[(metrics["promo_spend"] > 0) & (metrics["order_count"] == 0)]
    if not zero_sales.empty:
        lines.append("\n### 建议暂停/优化（有花费无成交）")
        for _, row in zero_sales.iterrows():
            lines.append(f"- **{row['product_name']}**：花费 {row['promo_spend']:.2f} 元，曝光 {row['exposure']:.0f}，但无订单")

    # 退款率高
    high_refund = metrics[(metrics["order_count"] >= 3) & (metrics["refund_rate"] > 30)]
    if not high_refund.empty:
        lines.append("\n### 退款率偏高")
        for _, row in high_refund.iterrows():
            lines.append(f"- **{row['product_name']}**：退款率 {row['refund_rate']:.2f}%")

    # 行动项
    lines.append("\n### 建议行动项")
    lines.append("1. 对低效商品降低出价或暂停计划，观察 1-2 天数据")
    lines.append("2. 对退款率高的商品检查详情页描述、SKU 规格和物流体验")
    lines.append("3. 对高效商品适度加预算，争取放大 GMV")

    return "\n".join(lines)


def generate_ai_report(
    kpis: Dict,
    metrics: pd.DataFrame,
    api_key: Optional[str] = None,
    base_url: str = "https://api.kimi.com/coding/v1",
    model: str = "kimi-coding",
    temperature: float = 1.0,
    reasoning_effort: str = "low",
    timeout: int = 60,
    max_completion_tokens: int = 16384,
    date: Optional[str] = None,
) -> Dict:
    """生成 AI 分析报告，失败时返回规则化洞察"""
    prompt = build_prompt(kpis, metrics, date)

    if api_key:
        try:
            content = call_llm(
                prompt, api_key, base_url, model,
                temperature, reasoning_effort, timeout=timeout,
                max_completion_tokens=max_completion_tokens,
            )
            content = content.strip() if content else ""
            if not content:
                raise RuntimeError("AI 返回内容为空")
            return {
                "source": "llm",
                "model": model,
                "content": content,
                "prompt": prompt,
                "error": None,
            }
        except Exception as e:
            return {
                "source": "rule_fallback",
                "model": model,
                "content": rule_based_insights(kpis, metrics),
                "prompt": prompt,
                "error": str(e),
            }
    else:
        return {
            "source": "rule",
            "model": None,
            "content": rule_based_insights(kpis, metrics),
            "prompt": prompt,
            "error": None,
        }
