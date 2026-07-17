"""
抖音日报生成器
"""

import datetime

from douyin_services import load_douyin_analysis
from douyin_storage import list_douyin_stores
from generic_report_builder import build_daily_report as _build_daily_report


def build_daily_report(report_date: datetime.date) -> str:
    return _build_daily_report(
        report_date,
        title="抖音推广日报",
        list_stores=list_douyin_stores,
        load_analysis=load_douyin_analysis,
    )
