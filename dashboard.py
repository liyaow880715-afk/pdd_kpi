"""
Streamlit 看板 UI 组件（深色版 + 多店铺 + 日期范围）
"""

import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from typing import Dict, List, Optional

from storage import list_available_stores, list_available_dates, list_store_records, _date_to_str
from store_manager import list_stores
from config_manager import get_config_defaults


def _auto_save_cost_callback():
    """成本表格自动保存回调"""
    import pandas as pd
    key = st.session_state.get("_cost_editor_key")
    store = st.session_state.get("_cost_editor_store")
    if not key or not store:
        return
    edited = st.session_state.get(key)
    if edited is None:
        return
    if isinstance(edited, dict):
        try:
            # 兼容 data_editor 在不同状态下返回的 dict（列长度可能不一致）
            edited = pd.DataFrame({k: pd.Series(v) for k, v in edited.items()})
        except Exception:
            return
    if not isinstance(edited, pd.DataFrame) or edited.empty:
        return
    from cost_manager import load_cost_config, save_cost_config, set_cost
    cfg = load_cost_config()
    for _, rec in edited.iterrows():
        code = str(rec.get("merchant_code", "")).strip()
        if not code:
            continue
        cfg = set_cost(
            cfg,
            store_name=store,
            merchant_code=code,
            product_name=rec.get("product_name", ""),
            product_cost=rec.get("product_cost", 0),
            logistics_cost=rec.get("logistics_cost", 0),
        )
    save_cost_config(cfg)


# 左侧导航选项
NAV_MODULES = [
    "📥 导入数据",
    "📋 订单明细",
    "🏠 店铺总览",
    "📊 核心指标",
    "🛒 商品分析",
    "🎨 样式分析",
    "💰 成本管理",
    "🤖 AI 洞察",
    "📅 历史数据",
    "⚙️ 店铺管理",
    "📢 企业微信报告",
    "📤 导出数据",
]

# 顶部配置选项
TOP_TABS = ["🏪 店铺切换", "⚙️ AI 配置"]


def load_css():
    """注入自定义 CSS 样式"""
    st.markdown(
        """
        <style>
        /* 全局深色背景 */
        .stApp {
            background: #0f1012;
        }
        /* 侧边栏整体 */
        [data-testid="stSidebar"] {
            background-color: #15161a;
            border-right: 1px solid #27282e;
        }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        /* 侧边栏标题区 */
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: #1f2026;
            border-radius: 14px;
            margin-bottom: 24px;
            border: 1px solid #2a2b32;
        }
        .sidebar-brand-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: #fff;
        }
        .sidebar-brand-text {
            color: #f0f0f5;
            font-size: 16px;
            font-weight: 700;
            line-height: 1.2;
        }
        .sidebar-brand-sub {
            color: #9ca3af;
            font-size: 11px;
            font-weight: 400;
        }
        /* 侧边栏导航菜单 */
        .sidebar-nav {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .sidebar-nav [data-testid="stRadio"] label {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 14px;
            border-radius: 10px;
            color: #d1d5db;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }
        .sidebar-nav [data-testid="stRadio"] label:hover {
            background-color: #1f2026;
            color: #fff;
        }
        .sidebar-nav [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        .sidebar-nav [role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(90deg, rgba(99,102,241,0.18) 0%, rgba(99,102,241,0.05) 100%);
            border: 1px solid rgba(99,102,241,0.35);
            color: #fff !important;
        }
        /* 顶部配置区 */
        .top-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .top-header [data-testid="stRadio"] > div {
            display: flex;
            gap: 8px;
            background: #1a1b1e;
            padding: 6px;
            border-radius: 12px;
            border: 1px solid #27282e;
        }
        .top-header [data-testid="stRadio"] label {
            padding: 8px 16px;
            border-radius: 8px;
            color: #9ca3af;
            font-size: 13px;
            font-weight: 500;
            border: none;
            background: transparent;
            cursor: pointer;
        }
        .top-header [data-testid="stRadio"] label:hover {
            color: #fff;
            background: #27282e;
        }
        .top-header [role="radiogroup"] > label:has(input:checked) {
            background: #6366f1 !important;
            color: #fff !important;
        }
        .top-header [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }
        /* 配置面板卡片 */
        .config-panel {
            background: #1a1b1e;
            border: 1px solid #27282e;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 24px;
        }
        /* 标题 */
        h1, h2, h3 {
            color: #f0f0f5;
            font-weight: 700;
        }
        /* KPI 卡片 */
        .kpi-card {
            background: #1a1b1e;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #27282e;
            border-left: 4px solid #6366f1;
            margin-bottom: 12px;
        }
        .kpi-label {
            font-size: 12px;
            color: #9ca3af;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 700;
            color: #f0f0f5;
        }
        .kpi-sub {
            font-size: 11px;
            color: #6b7280;
            margin-top: 4px;
        }
        .kpi-good { border-left-color: #22c55e; }
        .kpi-warn { border-left-color: #f59e0b; }
        .kpi-bad { border-left-color: #ef4444; }
        .kpi-info { border-left-color: #6366f1; }
        /* 店铺概览卡片 */
        .store-overview-card {
            background: #1a1b1e;
            border: 1px solid #27282e;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }
        .store-overview-title {
            font-size: 15px;
            font-weight: 600;
            color: #f0f0f5;
            margin-bottom: 12px;
        }
        .store-overview-metric {
            font-size: 20px;
            font-weight: 700;
            color: #f0f0f5;
        }
        .store-overview-label {
            font-size: 11px;
            color: #9ca3af;
        }
        /* 表格容器 */
        .stDataFrame, [data-testid="stDataFrame"] {
            border-radius: 12px;
            border: 1px solid #27282e;
        }
        /* 按钮 */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
        }
        /* 导入记录表格样式 */
        .import-record {
            background: #1a1b1e;
            border: 1px solid #27282e;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_nav(active_module: str = None) -> str:
    """渲染左侧功能导航，返回选中的模块"""
    if active_module is None:
        active_module = NAV_MODULES[0]

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">📊</div>
                <div>
                    <div class="sidebar-brand-text">拼多多推广 BI</div>
                    <div class="sidebar-brand-sub">多店铺推广数据分析工作台</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-nav">', unsafe_allow_html=True)
        selected = st.radio(
            "功能导航",
            options=NAV_MODULES,
            index=NAV_MODULES.index(active_module),
            label_visibility="collapsed",
            key="nav_module",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    return selected


def render_top_header(active_tab: str = None) -> str:
    """渲染顶部配置区 tabs，返回当前选中的 tab"""
    if active_tab is None:
        active_tab = TOP_TABS[0]
    st.markdown('<div class="top-header">', unsafe_allow_html=True)
    selected = st.radio(
        "顶部配置",
        options=TOP_TABS,
        index=TOP_TABS.index(active_tab),
        horizontal=True,
        label_visibility="collapsed",
        key="top_tab",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return selected


def render_store_selector(current_store_name: str = None, key: str = "store_selector") -> str:
    """渲染店铺选择下拉框"""
    stores = list_available_stores()
    if not stores:
        stores = ["默认店铺"]
    index = stores.index(current_store_name) if current_store_name in stores else 0
    return st.selectbox(
        "当前店铺",
        options=stores,
        index=index,
        key=key,
        help="切换要分析的店铺",
    )


def render_new_store_input() -> Optional[str]:
    """渲染新建店铺输入框，返回输入的名称"""
    st.markdown("---")
    st.caption("没有需要的店铺？可以新建一个")
    new_name = st.text_input("新建店铺名称", value="", key="new_store_name_input")
    return new_name.strip() or None


def render_date_range_selector(
    store_name: str,
    key: str = "date_range_selector",
) -> tuple:
    """渲染日期范围选择器，返回 (start_date, end_date)"""
    dates = list_available_dates(store_name)
    today = datetime.date.today()
    if dates:
        start_default = datetime.datetime.strptime(dates[0], "%Y-%m-%d").date()
        end_default = datetime.datetime.strptime(dates[-1], "%Y-%m-%d").date()
    else:
        start_default = today
        end_default = today

    # 限制最小最大可选日期
    min_date = datetime.date(2020, 1, 1)
    max_date = today

    selected = st.date_input(
        "分析日期范围",
        value=(start_default, end_default),
        min_value=min_date,
        max_value=max_date,
        key=key,
        help="选择要汇总分析的日期范围",
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        return selected
    return (selected, selected)


def render_store_tab(current_store_name: str = None) -> dict:
    """渲染顶部「店铺切换」面板，返回当前店铺与日期范围"""
    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    st.markdown("#### 🏪 店铺切换")
    col1, col2 = st.columns([1, 2])
    with col1:
        store_name = render_store_selector(current_store_name)
    with col2:
        start_date, end_date = render_date_range_selector(store_name)
    st.markdown("</div>", unsafe_allow_html=True)
    return {
        "store_name": store_name,
        "start_date": start_date,
        "end_date": end_date,
    }


def render_ai_tab(config: dict) -> dict:
    """渲染顶部「AI 配置」面板"""
    cfg = get_config_defaults() if config is None else config
    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    st.markdown("#### ⚙️ AI 配置")

    col1, col2 = st.columns(2)
    with col1:
        api_key = st.text_input(
            "API Key",
            type="password",
            value=cfg.get("api_key", ""),
            help="如 sk-kim...",
            key="ai_api_key",
        )
        base_url = st.text_input(
            "Base URL",
            value=cfg.get("base_url", "https://api.kimi.com/coding/v1"),
            help="Kimi coding: https://api.kimi.com/coding/v1",
            key="ai_base_url",
        )
        model = st.text_input(
            "模型名称",
            value=cfg.get("model", "kimi-coding"),
            help="如 kimi-coding / moonshot-v1-8k / gpt-4o",
            key="ai_model",
        )

    with col2:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(cfg.get("temperature", 1.0)),
            step=0.1,
            key="ai_temperature",
        )
        reasoning_options = ["low", "medium", "high"]
        reasoning_default = cfg.get("reasoning_effort", "low")
        reasoning_index = reasoning_options.index(reasoning_default) if reasoning_default in reasoning_options else 0
        reasoning_effort = st.selectbox(
            "Reasoning Effort",
            options=reasoning_options,
            index=reasoning_index,
            help="仅对 OpenAI o 系列推理模型生效",
            key="ai_reasoning_effort",
        )
        timeout = st.slider(
            "AI 请求超时(秒)",
            min_value=10,
            max_value=300,
            value=int(cfg.get("timeout", 60)),
            step=10,
            help="AI 接口最大等待时间",
            key="ai_timeout",
        )
        max_completion_tokens = st.slider(
            "单次最大输出 Token 数",
            min_value=1024,
            max_value=16384,
            value=int(cfg.get("max_completion_tokens", 16384)),
            step=1024,
            help="Kimi 思考模型会消耗 token 进行思考，若返回空内容请继续调大或换用 moonshot-v1-8k",
            key="ai_max_tokens",
        )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        save_clicked = st.button("💾 保存 AI 配置", use_container_width=True, key="ai_save_btn")
    with btn_col2:
        test_clicked = st.button("🧪 测试连接", use_container_width=True, key="ai_test_btn")

    st.markdown("</div>", unsafe_allow_html=True)

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "reasoning_effort": reasoning_effort,
        "timeout": timeout,
        "max_completion_tokens": max_completion_tokens,
        "ai_save_clicked": save_clicked,
        "ai_test_clicked": test_clicked,
    }


def kpi_card(label: str, value: str, sub: str = "", status: str = "info"):
    """渲染单个 KPI 卡片"""
    status_class = f"kpi-{status}"
    html = f"""
    <div class="kpi-card {status_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpis(kpis: Dict):
    """渲染 KPI 卡片"""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("推广总花费", f"¥{kpis['promo_spend']:,.2f}", "广告支出", "bad")
    with c2:
        kpi_card("推广 GMV", f"¥{kpis['promo_gmv']:,.2f}", "推广带来的交易额", "info")
    with c3:
        kpi_card("有效订单 GMV", f"¥{kpis['valid_order_gmv']:,.2f}", "剔除退款/取消", "info")
    with c4:
        kpi_card("有效商家实收", f"¥{kpis['valid_merchant_income']:,.2f}", "剔除退款/取消/待付款，已扣0.6%技术费", "good")

    c5, c6, c7, c8 = st.columns(4)
    roi_status = "good" if kpis["real_roi"] >= 2.5 else ("warn" if kpis["real_roi"] >= 1.5 else "bad")
    with c5:
        kpi_card("推广 ROI", f"{kpis['promo_roi']:.2f}", "GMV / 花费", "info")
    with c6:
        kpi_card("真实 ROI", f"{kpis['real_roi']:.2f}", "有效实收 / 花费", roi_status)
    with c7:
        kpi_card("有效订单 GMV ROI", f"{kpis['valid_order_gmv_roi']:.2f}", "有效 GMV / 花费", roi_status)
    with c8:
        kpi_card("点击率 CTR", f"{kpis['ctr']:.2f}%", "点击 / 曝光", "info")

    c9, c10, c11, c12 = st.columns(4)
    problem_status = "good" if kpis["problem_rate"] < 10 else ("warn" if kpis["problem_rate"] < 20 else "bad")
    with c9:
        kpi_card("订单总数", f"{kpis['order_count']:.0f}", f"有效 {kpis['valid_order_count']:.0f}", "info")
    with c10:
        kpi_card("推广成交笔数", f"{kpis['promo_orders']:.0f}", "归因到推广的订单", "info")
    with c11:
        kpi_card("退款率", f"{kpis['refund_rate']:.2f}%", f"{kpis['refund_count']:.0f} 笔", "bad")
    with c12:
        kpi_card("退款+取消率", f"{kpis['problem_rate']:.2f}%", f"{kpis['refund_count'] + kpis['cancel_count']:.0f} 笔", problem_status)

    # 成本 / 毛利 / 盈亏
    if "link_gross_profit" in kpis:
        c13, c14, c15, c16 = st.columns(4)
        profit_status = "good" if kpis.get("profit_loss", 0) >= 0 else "bad"
        with c13:
            kpi_card("总成本", f"¥{kpis.get('total_cost', 0):,.2f}", "商品+物流", "bad")
        with c14:
            kpi_card("链接毛利", f"¥{kpis.get('link_gross_profit', 0):,.2f}", "实收-成本", "info")
        with c15:
            kpi_card("盈亏", f"¥{kpis.get('profit_loss', 0):,.2f}", "毛利-推广花费", profit_status)
        with c16:
            kpi_card("毛利率", f"{kpis.get('gross_margin_rate', 0):.2f}%", "毛利/实收", "info")


def render_product_table(metrics: pd.DataFrame):
    """渲染商品明细表"""
    display_cols = [
        "product_name", "merchant_code", "promo_spend", "promo_gmv", "promo_roi",
        "valid_order_count", "valid_quantity", "valid_order_gmv", "valid_merchant_income",
        "real_roi_merchant_income", "valid_order_gmv_roi",
        "product_cost_unit", "logistics_cost_unit", "total_cost",
        "link_gross_profit", "profit_loss", "gross_margin_rate",
        "refund_rate", "cancel_rate", "problem_rate",
        "refund_unshipped_rate", "refund_shipped_rate", "refund_received_rate",
        "organic_ratio_gmv", "ctr", "click_to_order_rate"
    ]
    display_cols = [c for c in display_cols if c in metrics.columns]
    df = metrics[display_cols].copy()

    rename = {
        "product_name": "商品名称",
        "merchant_code": "商家编码",
        "promo_spend": "推广花费",
        "promo_gmv": "推广 GMV",
        "promo_roi": "推广 ROI",
        "valid_order_count": "有效订单数",
        "valid_quantity": "有效件数",
        "valid_order_gmv": "有效订单 GMV",
        "valid_merchant_income": "有效商家实收",
        "real_roi_merchant_income": "真实 ROI",
        "valid_order_gmv_roi": "有效 GMV ROI",
        "product_cost_unit": "商品成本/件",
        "logistics_cost_unit": "物流成本/件",
        "total_cost": "总成本",
        "link_gross_profit": "链接毛利",
        "profit_loss": "盈亏",
        "gross_margin_rate": "毛利率(%)",
        "refund_rate": "退款率(%)",
        "cancel_rate": "取消率(%)",
        "problem_rate": "问题率(%)",
        "refund_unshipped_rate": "未发货退款率(%)",
        "refund_shipped_rate": "已发货退款率(%)",
        "refund_received_rate": "已收货退款率(%)",
        "organic_ratio_gmv": "自然流量 GMV 占比(%)",
        "ctr": "点击率(%)",
        "click_to_order_rate": "点击转化率(%)",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    st.dataframe(
        df,
        use_container_width=True,
        height=500,
        column_config={
            "商品名称": st.column_config.TextColumn(width="large"),
            "真实 ROI": st.column_config.NumberColumn(format="%.2f"),
            "有效 GMV ROI": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_charts(metrics: pd.DataFrame, kpis: Dict):
    """渲染图表"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**推广 vs 自然流量 实收**")
        df_chart = metrics[["product_name", "promo_merchant_income", "organic_merchant_income"]].copy()
        df_chart = df_chart[df_chart["product_name"].notna()]
        df_chart = df_chart.sort_values("promo_merchant_income", ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_chart["product_name"],
            x=df_chart["promo_merchant_income"],
            name="推广实收（估算）",
            orientation="h",
            marker_color="#6366f1",
        ))
        fig.add_trace(go.Bar(
            y=df_chart["product_name"],
            x=df_chart["organic_merchant_income"],
            name="自然流量实收（估算）",
            orientation="h",
            marker_color="#22c55e",
        ))
        fig.update_layout(
            barmode="stack",
            xaxis_title="商家实收 (元)",
            yaxis_title="",
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f0f0f5"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**推广花费 vs 真实 ROI**")
        df_roi = metrics[metrics["promo_spend"] > 0].copy()
        df_roi = df_roi.sort_values("promo_spend", ascending=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=df_roi["product_name"],
            x=df_roi["promo_spend"],
            name="推广花费",
            orientation="h",
            marker_color="#f59e0b",
        ))
        fig2.add_trace(go.Scatter(
            y=df_roi["product_name"],
            x=df_roi["real_roi_merchant_income"],
            name="真实 ROI",
            mode="markers+text",
            text=[f"{v:.2f}" for v in df_roi["real_roi_merchant_income"]],
            textposition="middle right",
            marker=dict(size=12, color="#22c55e"),
            xaxis="x2",
        ))
        fig2.update_layout(
            xaxis=dict(title="推广花费 (元)"),
            xaxis2=dict(title="真实 ROI", overlaying="x", side="top"),
            yaxis_title="",
            height=400,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f0f0f5"),
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_style_table(style_metrics: pd.DataFrame):
    """渲染样式/规格分析表"""
    if style_metrics.empty:
        st.info("当前没有样式维度数据")
        return

    display_cols = [c for c in style_metrics.columns if c not in ["date"]]
    df = style_metrics[display_cols].copy()
    rename = {
        "product_id": "商品ID",
        "product_name": "商品名称",
        "product_name_raw": "商品名称",
        "style_id": "样式ID",
        "style_name": "规格",
        "style_name_raw": "规格",
        "order_count": "订单数",
        "valid_order_count": "有效订单数",
        "quantity": "件数",
        "valid_quantity": "有效件数",
        "order_gmv": "订单 GMV",
        "valid_order_gmv": "有效订单 GMV",
        "user_paid": "用户实付",
        "valid_user_paid": "有效用户实付",
        "merchant_income": "商家实收",
        "valid_merchant_income": "有效商家实收",
        "refund_count": "退款数",
        "cancel_count": "取消数",
        "refund_unshipped_count": "未发货退款数",
        "refund_shipped_count": "已发货退款数",
        "refund_received_count": "已收货退款数",
        "refund_rate": "退款率(%)",
        "cancel_rate": "取消率(%)",
        "refund_unshipped_rate": "未发货退款率(%)",
        "refund_shipped_rate": "已发货退款率(%)",
        "refund_received_rate": "已收货退款率(%)",
        "avg_order_gmv": "客单价",
        "avg_valid_order_gmv": "有效客单价",
        "avg_order_income": "单均实收",
        "avg_valid_order_income": "有效单均实收",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    st.dataframe(df, use_container_width=True, height=500)


def render_trend(history: pd.DataFrame, selected_stores: list = None):
    """渲染历史趋势"""
    if history.empty or "date" not in history.columns:
        st.info("导入多天的数据后可查看趋势")
        return

    st.markdown("**历史趋势**")

    if "store_name" in history.columns and selected_stores:
        history = history[history["store_name"].isin(selected_stores)]

    trend = history.groupby("date").agg({
        "promo_spend": "sum",
        "promo_gmv": "sum",
        "valid_order_gmv": "sum",
        "valid_merchant_income": "sum",
    }).reset_index()
    trend["promo_roi"] = trend["promo_gmv"] / trend["promo_spend"]
    trend["real_roi"] = trend["valid_merchant_income"] / trend["promo_spend"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["date"], y=trend["promo_spend"], name="推广花费", mode="lines+markers", line=dict(color="#ef4444")))
    fig.add_trace(go.Scatter(x=trend["date"], y=trend["promo_gmv"], name="推广 GMV", mode="lines+markers", line=dict(color="#6366f1")))
    fig.add_trace(go.Scatter(x=trend["date"], y=trend["valid_order_gmv"], name="有效订单 GMV", mode="lines+markers", line=dict(color="#22c55e")))
    fig.add_trace(go.Scatter(x=trend["date"], y=trend["valid_merchant_income"], name="有效商家实收", mode="lines+markers", line=dict(color="#f59e0b")))
    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="金额 (元)",
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=trend["date"], y=trend["promo_roi"], name="推广 ROI", mode="lines+markers", line=dict(color="#6366f1")))
    fig2.add_trace(go.Scatter(x=trend["date"], y=trend["real_roi"], name="真实 ROI", mode="lines+markers", line=dict(color="#22c55e")))
    fig2.update_layout(
        xaxis_title="日期",
        yaxis_title="ROI",
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ===========================
# 新增：导入数据、店铺总览、历史数据、店铺管理 UI
# ===========================


def render_import_module(store_name: str) -> dict:
    """渲染导入数据模块，返回用户输入与操作状态"""
    st.subheader("📥 导入数据")
    st.caption(f"正在为店铺「{store_name}」导入每日推广与订单数据")

    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        import_date = st.date_input(
            "数据日期",
            value=datetime.date.today(),
            key="import_date",
        )
        promo_file = st.file_uploader(
            "推广数据 (.xls / .xlsx)",
            type=["xls", "xlsx"],
            key="import_promo_file",
        )
    with col2:
        st.write("")  # 占位对齐
        order_file = st.file_uploader(
            "订单数据 (.csv)",
            type=["csv"],
            key="import_order_file",
        )

    has_files = promo_file is not None and order_file is not None
    exists = False
    if has_files:
        from storage import record_exists
        exists = record_exists(store_name, import_date)
        if exists:
            st.warning(f"⚠️ {store_name} {import_date} 的数据已存在，导入将覆盖旧数据。")

    import_clicked = st.button(
        "✅ 确认导入",
        use_container_width=True,
        type="primary",
        disabled=not has_files,
        key="import_confirm_btn",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    return {
        "import_date": import_date,
        "promo_file": promo_file,
        "order_file": order_file,
        "import_clicked": import_clicked,
        "overwrite": exists,
    }


def render_recent_imports(store_name: str, limit: int = 10):
    """渲染最近导入记录"""
    st.markdown("#### 最近导入记录")
    records = list_store_records(store_name)
    if not records:
        st.info("暂无导入记录")
        return

    for rec in reversed(records[-limit:]):
        with st.container():
            c1, c2, c3 = st.columns([3, 4, 2])
            with c1:
                st.write(f"**{rec.get('store_name', '-')}**")
                st.caption(f"📅 {rec.get('date', '-')}")
            with c2:
                st.caption(
                    f"商品 {rec.get('product_rows', 0)} 行 / 样式 {rec.get('style_rows', 0)} 行 / 订单 {rec.get('order_rows', 0)} 行"
                )
            with c3:
                st.caption(f"🕒 {rec.get('saved_at', '-')[:10]}")
        st.divider()


def render_order_detail_module(store_name: str) -> dict:
    """渲染订单明细模块，支持查看订单并按商品 ID 维护商家编码"""
    st.subheader("📋 订单明细")
    st.caption("查看已导入订单，按商品维护商家编码后可在「成本管理」维护成本")

    from storage import load_daily_orders, list_available_dates

    dates = list_available_dates(store_name)
    if not dates:
        st.info("暂无订单数据，请先在「导入数据」中上传。")
        return {"action": None}

    selected_date = st.selectbox(
        "选择日期",
        options=dates,
        key="order_detail_date_select",
    )

    try:
        orders = load_daily_orders(selected_date, store_name)
    except Exception as e:
        st.error(f"加载订单失败: {e}")
        return {"action": None}

    if orders.empty:
        st.info(f"{selected_date} 暂无订单数据")
        return {"action": None}

    orders = orders.copy()
    if "merchant_code" not in orders.columns:
        orders["merchant_code"] = ""
    orders["merchant_code"] = orders["merchant_code"].fillna("").astype(str).str.strip()

    missing_mask = orders["merchant_code"] == ""
    st.markdown(
        f"**{selected_date}** 共 **{len(orders)}** 笔订单，"
        f"**{missing_mask.sum()}** 笔缺少商家编码"
    )

    # 商品维度汇总
    if "product_id" not in orders.columns or orders["product_id"].isna().all():
        st.info("订单数据缺少商品 ID，无法展示商品维度")
        return {"action": None}

    product_summary = (
        orders.dropna(subset=["product_id"])
        .groupby("product_id", as_index=False)
        .agg(
            product_name=("product_name", "first"),
            style_name=("style_name", "first"),
            merchant_code=("merchant_code", lambda x: x[x.astype(str).str.strip() != ""].iloc[0] if any(x.astype(str).str.strip() != "") else ""),
            order_count=("order_id", "count"),
        )
    )
    product_summary["product_id_str"] = product_summary["product_id"].apply(lambda x: str(x).strip().removesuffix(".0"))

    show_missing_only = st.checkbox("仅显示缺少商家编码的商品", value=False, key="order_detail_missing_only")
    summary_display = product_summary[product_summary["merchant_code"] == ""] if show_missing_only else product_summary

    st.markdown("##### 商品商家编码一览")
    show_cols = ["product_id_str", "product_name", "style_name", "merchant_code", "order_count"]
    show_cols = [c for c in show_cols if c in summary_display.columns]
    st.dataframe(
        summary_display[show_cols].rename(columns={"product_id_str": "商品ID"}),
        use_container_width=True,
        height=300,
    )

    with st.expander("查看原始订单明细"):
        display_cols = [
            "pay_time", "order_id", "product_id", "product_name", "style_name",
            "merchant_code", "order_status", "aftersales_status",
            "quantity", "item_total", "user_paid", "merchant_income",
        ]
        display_cols = [c for c in display_cols if c in orders.columns]
        st.dataframe(orders[display_cols], use_container_width=True, height=400)

    # 维护/补充商家编码
    st.markdown("---")
    st.markdown("##### 维护商品商家编码")

    product_options = {}
    for _, row in product_summary.iterrows():
        pid = row["product_id_str"]
        label = f"{row['product_name']}（ID: {pid}，当前: {row['merchant_code'] or '无'}）"
        product_options[label] = pid

    selected_label = st.selectbox(
        "选择商品",
        options=list(product_options.keys()),
        key="order_detail_product_select",
    )
    selected_pid = product_options[selected_label]
    current_code = product_summary.set_index("product_id_str").at[selected_pid, "merchant_code"]

    c1, c2 = st.columns([1, 2])
    with c1:
        st.text_input("当前商家编码", value=current_code, disabled=True, key="order_detail_current_code")
    with c2:
        new_code = st.text_input(
            "新商家编码",
            placeholder="输入或修改该商品的商家编码",
            key="order_detail_new_code",
        )

    save_clicked = st.button(
        "💾 保存映射",
        use_container_width=True,
        type="primary",
        key="order_detail_save_mapping",
    )

    if save_clicked and new_code.strip():
        return {
            "action": "save_product_merchant_mapping",
            "product_id": selected_pid,
            "merchant_code": new_code.strip(),
        }

    return {"action": None}


def render_store_overview(config: dict = None):
    """渲染店铺总览（多店对比），按顶部所选日期范围汇总"""
    st.subheader("🏠 店铺总览")
    st.caption("对比所选日期范围内各店铺的汇总表现")

    from metrics import (
        compute_overall_kpis,
        aggregate_product_metrics,
        compute_product_metrics,
        merge_refund_stage_counts,
    )
    from storage import load_daily_data, load_daily_orders, list_available_dates
    from cost_manager import apply_costs_to_metrics

    config = config or {}
    start_date = config.get("start_date", datetime.date.today())
    end_date = config.get("end_date", datetime.date.today())
    start_s = _date_to_str(start_date)
    end_s = _date_to_str(end_date)

    stores = list_available_stores()
    if not stores:
        st.info("暂无店铺数据，请先在「导入数据」中上传。")
        return

    overview_rows = []
    for store in stores:
        dates = [d for d in list_available_dates(store) if start_s <= d <= end_s]
        if not dates:
            continue
        dfs = []
        order_dfs = []
        for d in dates:
            try:
                metrics, _ = load_daily_data(d, store)
                metrics = apply_costs_to_metrics(metrics, store)
                dfs.append(metrics)
            except Exception:
                continue
            try:
                orders = load_daily_orders(d, store)
                if not orders.empty:
                    order_dfs.append(orders)
            except Exception:
                continue
        if not dfs:
            continue
        try:
            metrics = aggregate_product_metrics(dfs)
            metrics = merge_refund_stage_counts(metrics, order_dfs)
            metrics = compute_product_metrics(metrics)
            kpis = compute_overall_kpis(metrics)
            overview_rows.append({
                "店铺": store,
                "统计日期": f"{start_s} ~ {end_s}",
                "推广花费": kpis.get("promo_spend", 0),
                "推广 GMV": kpis.get("promo_gmv", 0),
                "有效商家实收": kpis.get("valid_merchant_income", 0),
                "推广 ROI": kpis.get("promo_roi", 0),
                "真实 ROI": kpis.get("real_roi", 0),
                "盈亏": kpis.get("profit_loss", 0),
                "退款率": kpis.get("refund_rate", 0),
                "未发货退款率": kpis.get("refund_unshipped_rate", 0),
                "已发货退款率": kpis.get("refund_shipped_rate", 0),
                "已收货退款率": kpis.get("refund_received_rate", 0),
                "取消率": kpis.get("cancel_rate", 0),
                "订单数": kpis.get("order_count", 0),
            })
        except Exception:
            continue

    if not overview_rows:
        st.info("店铺数据加载失败")
        return

    overview_df = pd.DataFrame(overview_rows)

    # 店铺 KPI 卡片
    cols = st.columns(len(overview_rows))
    for idx, row in enumerate(overview_rows):
        with cols[idx]:
            roi_status = "good" if row["真实 ROI"] >= 2.5 else ("warn" if row["真实 ROI"] >= 1.5 else "bad")
            profit_status = "good" if row["盈亏"] >= 0 else "bad"
            st.markdown(
                f"""
                <div class="store-overview-card">
                    <div class="store-overview-title">{row['店铺']}</div>
                    <div style="margin-bottom:10px;">
                        <span class="store-overview-metric">¥{row['真实 ROI']:.2f}</span>
                        <span class="store-overview-label"> 真实 ROI</span>
                    </div>
                    <div style="margin-bottom:6px;">
                        <span class="store-overview-metric">¥{row['有效商家实收']:,.0f}</span>
                        <span class="store-overview-label"> 有效实收</span>
                    </div>
                    <div style="margin-bottom:6px;">
                        <span class="store-overview-metric">¥{row['盈亏']:,.0f}</span>
                        <span class="store-overview-label"> 盈亏</span>
                    </div>
                    <div>
                        <span class="store-overview-label">统计 {row['统计日期']} · 花费 ¥{row['推广花费']:,.0f}<br/>退款 {row['退款率']:.1f}%（未发{row['未发货退款率']:.1f}% / 已发{row['已发货退款率']:.1f}% / 已收{row['已收货退款率']:.1f}%） · 取消 {row['取消率']:.1f}%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### 店铺对比明细")
    st.dataframe(
        overview_df,
        use_container_width=True,
        column_config={
            "推广花费": st.column_config.NumberColumn(format="¥%.0f"),
            "推广 GMV": st.column_config.NumberColumn(format="¥%.0f"),
            "有效商家实收": st.column_config.NumberColumn(format="¥%.0f"),
            "推广 ROI": st.column_config.NumberColumn(format="%.2f"),
            "真实 ROI": st.column_config.NumberColumn(format="%.2f"),
            "盈亏": st.column_config.NumberColumn(format="¥%.0f"),
            "退款率": st.column_config.NumberColumn(format="%.2f%%"),
            "未发货退款率": st.column_config.NumberColumn(format="%.2f%%"),
            "已发货退款率": st.column_config.NumberColumn(format="%.2f%%"),
            "已收货退款率": st.column_config.NumberColumn(format="%.2f%%"),
            "取消率": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    # 多店趋势
    st.markdown("#### 多店历史趋势")
    history = load_all_product_history(stores, start_date, end_date)
    render_trend(history, stores)


def render_history_module(store_name: str) -> dict:
    """渲染历史数据模块，返回操作指令"""
    st.subheader("📅 历史数据")
    st.caption(f"查看 {store_name} 的已保存记录")

    records = list_store_records(store_name)
    if not records:
        st.info("该店铺暂无历史数据")
        return {"action": None}

    st.markdown("#### 已保存日期")
    dates = [r["date"] for r in records]
    selected_date = st.selectbox("选择日期查看详情", options=dates, key="history_date_select")

    from storage import load_daily_data
    if selected_date:
        try:
            metrics, style_metrics = load_daily_data(selected_date, store_name)
            st.success(f"已加载 {store_name} {selected_date} 的数据")

            c1, c2 = st.columns([4, 1])
            with c1:
                tab1, tab2 = st.tabs(["商品指标", "样式指标"])
                with tab1:
                    render_product_table(metrics)
                with tab2:
                    render_style_table(style_metrics)
            with c2:
                st.warning("删除后不可恢复")
                if st.button("🗑️ 删除该日数据", key=f"delete_history_{store_name}_{selected_date}"):
                    return {
                        "action": "delete_record",
                        "store_name": store_name,
                        "date": selected_date,
                    }
        except Exception as e:
            st.error(f"加载失败: {e}")

    return {"action": None}


def render_store_management():
    """渲染店铺管理模块"""
    st.subheader("⚙️ 店铺管理")

    stores = list_stores()

    # 新建店铺始终显示在最上方
    st.markdown("#### 新建店铺")
    with st.form("create_store_form", clear_on_submit=True):
        new_name = st.text_input("店铺名称", value="", key="mgmt_new_store_name", placeholder="如：旗舰店、分销店")
        create_submitted = st.form_submit_button("➕ 创建店铺", use_container_width=True)
    if create_submitted and new_name.strip():
        return {"action": "create", "new_name": new_name.strip()}

    st.markdown("---")

    if not stores:
        st.info("暂无店铺，请在上方创建")
        return

    for store in stores:
        with st.container():
            cols = st.columns([3, 2, 1])
            with cols[0]:
                st.write(f"**{store['name']}**")
                st.caption(f"ID: {store['id']} · 创建于 {store.get('created_at', '-')[:10]}")
            with cols[1]:
                new_name = st.text_input(
                    "重命名",
                    value=store["name"],
                    key=f"rename_{store['id']}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                rename_btn = st.button("保存", key=f"rename_btn_{store['id']}")
                delete_btn = st.button("🗑️ 删除", key=f"delete_btn_{store['id']}")

            if rename_btn and new_name.strip() and new_name.strip() != store["name"]:
                return {"action": "rename", "store_id": store["id"], "new_name": new_name.strip()}
            if delete_btn:
                return {"action": "delete", "store_id": store["id"], "store_name": store["name"]}
        st.divider()

    return {"action": None}


def render_cost_module(store_name: str) -> dict:
    """渲染成本管理模块，返回操作指令"""
    st.subheader("💰 成本管理")
    st.caption("按商家编码维护商品成本和物流成本，用于计算链接毛利与盈亏")

    from cost_manager import (
        load_cost_config,
        export_costs_to_csv,
        import_costs_from_csv,
    )

    cfg = load_cost_config()
    saved_costs = cfg.get("merchant_costs", {}).get(store_name, {})

    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    st.markdown("#### 商家编码成本维护")
    st.caption("修改成本后点击「保存全部」；点击「从订单重新提取」只会追加新编码，不会覆盖已有成本。")

    rows = []
    for code in sorted(saved_costs.keys()):
        info = saved_costs.get(code, {})
        rows.append({
            "merchant_code": code,
            "product_name": info.get("product_name", ""),
            "product_cost": float(info.get("product_cost", 0) or 0),
            "logistics_cost": float(info.get("logistics_cost", 0) or 0),
        })

    if not rows:
        st.info("当前店铺暂无商家编码数据。请先导入订单，再点击「从订单重新提取」。")
        df = pd.DataFrame(columns=["merchant_code", "product_name", "product_cost", "logistics_cost"])
    else:
        df = pd.DataFrame(rows)

    import re

    if not df.empty:
        with st.form("cost_edit_form"):
            st.markdown("**现有编码成本**")
            # 表头
            hc1, hc2, hc3, hc4 = st.columns([2, 2, 1, 1])
            hc1.write("商家编码")
            hc2.write("商品名称")
            hc3.write("商品成本/件")
            hc4.write("物流成本/件")

            edited_rows = []
            for _, row in df.iterrows():
                code = str(row["merchant_code"])
                safe_key = re.sub(r"\W+", "_", code)[:50]
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                with c1:
                    st.text_input(
                        "商家编码",
                        value=code,
                        disabled=True,
                        label_visibility="collapsed",
                        key=f"ce_code_{safe_key}",
                    )
                with c2:
                    name = st.text_input(
                        "商品名称",
                        value=str(row["product_name"]),
                        label_visibility="collapsed",
                        key=f"ce_name_{safe_key}",
                    )
                with c3:
                    pc = st.number_input(
                        "商品成本/件",
                        value=float(row["product_cost"]),
                        step=0.01,
                        label_visibility="collapsed",
                        key=f"ce_pc_{safe_key}",
                    )
                with c4:
                    lc = st.number_input(
                        "物流成本/件",
                        value=float(row["logistics_cost"]),
                        step=0.01,
                        label_visibility="collapsed",
                        key=f"ce_lc_{safe_key}",
                    )
                edited_rows.append({
                    "merchant_code": code,
                    "product_name": name,
                    "product_cost": pc,
                    "logistics_cost": lc,
                })
            save_all = st.form_submit_button("💾 保存全部", use_container_width=True)
    else:
        edited_rows = []
        save_all = False

    st.markdown("##### 手动添加新编码")
    with st.form("add_cost_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            new_code = st.text_input("商家编码", key="cost_new_code")
        with c2:
            new_name = st.text_input("商品名称", key="cost_new_name")
        with c3:
            new_pc = st.number_input("商品成本/件", value=0.0, step=0.01, key="cost_new_pc")
        with c4:
            new_lc = st.number_input("物流成本/件", value=0.0, step=0.01, key="cost_new_lc")
        add_submitted = st.form_submit_button("➕ 添加", use_container_width=True)

    refresh_clicked = st.button(
        "🔄 从订单重新提取（仅追加新编码）",
        use_container_width=True,
        key="cost_refresh_btn",
    )

    st.markdown("---")
    st.markdown("##### 批量导入 / 导出")
    c1, c2 = st.columns(2)
    with c1:
        csv_text = export_costs_to_csv(store_name)
        st.download_button(
            label="📥 导出成本 CSV",
            data=csv_text,
            file_name=f"costs_{store_name}.csv",
            mime="text/csv",
            use_container_width=True,
            key="cost_export_btn",
        )
    with c2:
        import_file = st.file_uploader(
            "导入成本 CSV",
            type=["csv"],
            key="cost_import_file",
        )
        import_clicked = st.button(
            "📤 导入并更新",
            use_container_width=True,
            key="cost_import_btn",
            disabled=(import_file is None),
        )

    st.markdown("</div>", unsafe_allow_html=True)

    action = None
    payload = {}
    if add_submitted and new_code.strip():
        action = "add_cost"
        payload = {
            "merchant_code": new_code.strip(),
            "product_name": new_name.strip(),
            "product_cost": new_pc,
            "logistics_cost": new_lc,
        }
    elif save_all:
        action = "save_costs"
        payload = {"costs": edited_rows}
    elif import_clicked and import_file is not None:
        action = "import_costs"
        payload = {"file": import_file}
    elif refresh_clicked:
        action = "refresh_cost_codes"

    if action:
        return {"action": action, **payload}
    return {"action": None}


def render_wecom_module() -> dict:
    """渲染企业微信报告模块，返回操作指令"""
    st.subheader("📢 企业微信报告")
    st.caption("基于「智能机器人长连接」主动推送昨日 + 本月累计汇总报告")

    from wecom import load_wecom_config, save_wecom_config, test_wecom_connection
    from report_builder import preview_report

    cfg = load_wecom_config()

    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    st.markdown("#### 智能机器人配置")

    bot_id = st.text_input(
        "智能机器人 BotID",
        value=cfg.get("bot_id", ""),
        help="企业微信管理后台智能机器人详情页的 BotID",
        key="wecom_bot_id",
    )
    secret = st.text_input(
        "智能机器人 Secret",
        value=cfg.get("secret", ""),
        type="password",
        help="长连接专用 Secret",
        key="wecom_secret",
    )

    chatid = st.text_input(
        "群聊 / 用户 ID (ChatID)",
        value=cfg.get("chatid", ""),
        help="群聊ID 可在群里 @机器人后点击「获取群聊ID」自动填入；单聊填写用户 userid",
        key="wecom_chatid",
    )

    chat_type_option = st.radio(
        "会话类型",
        options=["group", "single"],
        index=0 if int(cfg.get("chat_type", 2)) == 2 else 1,
        format_func=lambda x: "群聊" if x == "group" else "单聊",
        key="wecom_chat_type",
        horizontal=True,
    )
    chat_type = 2 if chat_type_option == "group" else 1

    timeout = st.slider(
        "请求超时(秒)",
        min_value=5,
        max_value=60,
        value=int(cfg.get("timeout", 30)),
        step=5,
        key="wecom_timeout",
    )

    new_cfg = {
        "send_type": "aibot",
        "bot_id": bot_id.strip(),
        "secret": secret.strip(),
        "chatid": chatid.strip(),
        "chat_type": chat_type,
        "timeout": timeout,
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        save_clicked = st.button("💾 保存配置", use_container_width=True, key="wecom_save_btn")
    with c2:
        test_clicked = st.button("🧪 测试连接", use_container_width=True, key="wecom_test_btn")
    with c3:
        listen_clicked = st.button("🔍 获取群聊ID", use_container_width=True, key="wecom_listen_btn")

    st.markdown("</div>", unsafe_allow_html=True)

    if save_clicked:
        save_wecom_config(new_cfg)
        st.success("企业微信配置已保存")

    if test_clicked:
        with st.spinner("正在测试企业微信连接..."):
            result = test_wecom_connection(new_cfg)
            if result["ok"]:
                st.success(result.get("message", "测试通过"))
            else:
                st.error(f"测试失败: {result.get('error', '未知错误')}")

    if listen_clicked:
        if not bot_id or not secret:
            st.error("请先填写 BotID 和 Secret")
        else:
            return {"action": "listen", "config": new_cfg}

    # 报告预览
    st.markdown("#### 报告预览")
    report_date = st.date_input("报告日期（汇总前一天数据）", value=datetime.date.today(), key="wecom_report_date")
    report_content = preview_report(report_date)
    st.text_area("报告内容", report_content, height=300, key="wecom_report_preview")

    send_clicked = st.button(
        "📤 发送昨日汇总报告",
        use_container_width=True,
        type="primary",
        key="wecom_send_btn",
    )

    if send_clicked:
        return {"action": "send_report", "config": new_cfg, "report_date": report_date}

    return {"action": None}


def load_all_product_history(
    store_names: Optional[List[str]] = None,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """加载指定店铺、日期范围内的历史商品级数据用于趋势分析"""
    from storage import load_daily_data, list_available_dates, list_available_stores
    all_dates = list_available_dates()
    if start_date and end_date:
        start_s = _date_to_str(start_date)
        end_s = _date_to_str(end_date)
        dates = [d for d in all_dates if start_s <= d <= end_s]
    else:
        dates = all_dates
    stores = store_names or list_available_stores()
    dfs = []
    for store in stores:
        for d in dates:
            try:
                df, _ = load_daily_data(d, store)
                dfs.append(df)
            except Exception:
                continue
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)
