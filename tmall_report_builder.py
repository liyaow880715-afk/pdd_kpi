"""
天猫日报生成器
"""

import datetime

from generic_report_builder import build_daily_report as _build_daily_report
from tmall_services import load_tmall_analysis
from tmall_storage import list_tmall_stores


def build_daily_report(report_date: datetime.date) -> str:
    return _build_daily_report(
        report_date,
        title="天猫推广日报",
        list_stores=list_tmall_stores,
        load_analysis=load_tmall_analysis,
    )
