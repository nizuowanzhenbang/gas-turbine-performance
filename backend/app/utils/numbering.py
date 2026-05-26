"""业务编号生成器：保证全局唯一。

所有编号格式：
  - PERF-YYYYMMDD-NNNN  每日批次性能计算
  - DEG-YYYYMM-NN       月度退化记录
  - AL-YYYYMMDD-NNNN    每日告警
"""
from datetime import datetime, date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.performance import PerformanceCalculation, DegradationRecord
from app.models.alert import Alert


def _today_prefix(d: date | None = None) -> str:
    return (d or date.today()).strftime("%Y%m%d")


def _month_prefix(d: date | None = None) -> str:
    return (d or date.today()).strftime("%Y%m")


def next_perf_batch_no(db: Session, when: datetime | None = None) -> str:
    prefix = f"PERF-{_today_prefix(when.date() if when else None)}-"
    stmt = select(func.count()).select_from(PerformanceCalculation).where(
        PerformanceCalculation.batch_no.like(prefix + "%")
    )
    seq = db.scalar(stmt) or 0
    return f"{prefix}{seq + 1:04d}"


def next_degradation_no(db: Session, when: date | None = None) -> str:
    prefix = f"DEG-{_month_prefix(when)}-"
    stmt = select(func.count()).select_from(DegradationRecord).where(
        DegradationRecord.record_no.like(prefix + "%")
    )
    seq = db.scalar(stmt) or 0
    return f"{prefix}{seq + 1:02d}"


def next_alert_no(db: Session, when: datetime | None = None) -> str:
    prefix = f"AL-{_today_prefix(when.date() if when else None)}-"
    stmt = select(func.count()).select_from(Alert).where(
        Alert.alert_no.like(prefix + "%")
    )
    seq = db.scalar(stmt) or 0
    return f"{prefix}{seq + 1:04d}"
