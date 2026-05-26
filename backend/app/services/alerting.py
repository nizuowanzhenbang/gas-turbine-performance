"""告警写入服务：同对象 + 同 category + OPEN 状态自动去重，避免风暴。"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertLevel, AlertStatus
from app.utils.numbering import next_alert_no


def emit_alert(
    db: Session,
    *,
    gas_turbine_id: int | None,
    cc_unit_id: int | None,
    category: str,
    level: AlertLevel,
    title: str,
    description: str = "",
    measured_value: float | None = None,
    threshold: float | None = None,
    unit: str = "",
) -> Alert:
    """新建或更新一条 OPEN 告警。

    去重原则：若同一对象（gas_turbine_id, cc_unit_id 任一匹配）+ 同 category 的
    OPEN 告警已存在，则只刷新 measured_value / triggered_at，不再新发。
    """
    q = db.query(Alert).filter(
        Alert.category == category,
        Alert.status == AlertStatus.OPEN,
    )
    if gas_turbine_id is not None:
        q = q.filter(Alert.gas_turbine_id == gas_turbine_id)
    if cc_unit_id is not None:
        q = q.filter(Alert.cc_unit_id == cc_unit_id)
    existing = q.first()

    now = datetime.now(timezone.utc)
    if existing:
        existing.measured_value = measured_value
        existing.threshold = threshold
        existing.triggered_at = now
        if existing.level != level:
            existing.level = level
        db.commit()
        db.refresh(existing)
        return existing

    a = Alert(
        alert_no=next_alert_no(db, now),
        gas_turbine_id=gas_turbine_id,
        cc_unit_id=cc_unit_id,
        category=category,
        level=level,
        status=AlertStatus.OPEN,
        title=title,
        description=description,
        measured_value=measured_value,
        threshold=threshold,
        unit=unit,
        triggered_at=now,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a
