"""APScheduler 定时任务。

- perf_calc_job        : 每 N 分钟为每台 RUNNING 燃机跑一次 ISO 性能计算
- health_check_job     : 每 5 分钟扫一次最新读数，振动 / EGT 散布 / 轴位移 → 告警
- degradation_daily_job: 每日凌晨 2 点汇总过去 7 天退化率，必要时落 DegradationRecord
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.alert import AlertLevel
from app.models.equipment import EquipmentStatus, GasTurbine
from app.models.performance import DegradationRecord, PerformanceCalculation
from app.models.reading import OperationReading
from app.services import performance_calc as pc
from app.services.alerting import emit_alert
from app.services.integration_client import (
    push_defect_to_inspection,
    push_performance_snapshot_to_fuel_metering,
    push_safety_event,
)
from app.services.perf_engine import compute_for_window
from app.utils.numbering import next_degradation_no

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ============================================================================
# Jobs
# ============================================================================

def perf_calc_job() -> None:
    """每分钟扫一次：为每台 RUNNING 燃机算最近 15 分钟性能并入库。"""
    db = SessionLocal()
    try:
        running = db.scalars(
            select(GasTurbine).where(GasTurbine.status == EquipmentStatus.RUNNING)
        ).all()
        for gt in running:
            try:
                record = compute_for_window(db, gt.id, window_minutes=15)
                if record and record.power_deviation_pct >= 3.0:
                    alert = emit_alert(
                        db,
                        gas_turbine_id=gt.id,
                        cc_unit_id=None,
                        category="DEGRADATION",
                        level=AlertLevel.WARNING if record.power_deviation_pct < 5 else AlertLevel.CRITICAL,
                        title=f"{gt.code} 性能退化 {record.power_deviation_pct:.2f}%",
                        description="出力较基准下降超过阈值，建议安排在线水洗或巡检",
                        measured_value=record.power_deviation_pct,
                        threshold=3.0,
                        unit="%",
                    )
                    if alert.level == AlertLevel.CRITICAL and not alert.pushed_to_inspection:
                        ok = push_defect_to_inspection(
                            alert_no=alert.alert_no,
                            gas_turbine_code=gt.code,
                            category="DEGRADATION",
                            title=alert.title,
                            description=alert.description,
                            measured_value=alert.measured_value,
                            threshold=alert.threshold,
                            unit=alert.unit,
                        )
                        alert.pushed_to_inspection = ok
                        alert.push_remarks = (alert.push_remarks + (" | pushed→inspection" if ok else " | inspection-push-failed")).strip(" |")
                        db.commit()
                if record:
                    push_performance_snapshot_to_fuel_metering(
                        gas_turbine_code=gt.code,
                        corrected_efficiency=record.corrected_efficiency,
                        corrected_heat_rate_kj_kwh=record.corrected_heat_rate_kj_kwh,
                        measured_power_mw=record.measured_power_mw,
                        calc_time_iso=record.calc_time.isoformat(),
                    )
            except Exception:
                logger.exception("perf_calc_job failed for %s", gt.code)
    finally:
        db.close()


def health_check_job() -> None:
    """每 5 分钟：扫最新一条读数 → 振动 / EGT 散布 / 轴位移 触发告警"""
    db = SessionLocal()
    try:
        running = db.scalars(
            select(GasTurbine).where(GasTurbine.status == EquipmentStatus.RUNNING)
        ).all()
        for gt in running:
            latest: OperationReading | None = (
                db.query(OperationReading)
                .filter(OperationReading.gas_turbine_id == gt.id)
                .order_by(OperationReading.timestamp.desc())
                .first()
            )
            if not latest:
                continue
            try:
                _check_vibration(db, gt, latest)
                _check_egt_spread(db, gt, latest)
                _check_axial_displacement(db, gt, latest)
            except Exception:
                logger.exception("health_check_job failed for %s", gt.code)
    finally:
        db.close()


def _check_vibration(db, gt: GasTurbine, latest: OperationReading) -> None:
    zone = pc.vibration_alarm_level(latest.vibration_mm_s)
    if zone in ("A", "B"):
        return
    level = AlertLevel.WARNING if zone == "C" else AlertLevel.CRITICAL
    alert = emit_alert(
        db,
        gas_turbine_id=gt.id,
        cc_unit_id=None,
        category="VIBRATION",
        level=level,
        title=f"{gt.code} 振动 {latest.vibration_mm_s:.2f} mm/s 进入 {zone} 区",
        description="ISO 10816 振动等级超阈，需安排停机检查或加密监测",
        measured_value=latest.vibration_mm_s,
        threshold=4.5 if zone == "C" else 7.1,
        unit="mm/s",
    )
    if alert.level == AlertLevel.CRITICAL and not alert.pushed_to_safety:
        ok = push_safety_event(
            alert_no=alert.alert_no,
            gas_turbine_code=gt.code,
            title=alert.title,
            description=alert.description,
        )
        alert.pushed_to_safety = ok
        alert.push_remarks = (alert.push_remarks + (" | pushed→safety" if ok else " | safety-push-failed")).strip(" |")
        db.commit()


def _check_egt_spread(db, gt: GasTurbine, latest: OperationReading) -> None:
    tcs = [latest.egt_t1_c, latest.egt_t2_c, latest.egt_t3_c, latest.egt_t4_c, latest.egt_t5_c, latest.egt_t6_c]
    stats = pc.egt_statistics(tcs, spread_warn_c=50.0)
    if stats.spread_c < 50.0:
        return
    emit_alert(
        db,
        gas_turbine_id=gt.id,
        cc_unit_id=None,
        category="EGT_SPREAD",
        level=AlertLevel.WARNING if stats.spread_c < 80 else AlertLevel.CRITICAL,
        title=f"{gt.code} EGT 散布 {stats.spread_c:.1f}°C（疑似热电偶 #{stats.suspect_thermocouple}）",
        description="排气温度热电偶分散度超阈，可能是某燃烧器/喷嘴异常",
        measured_value=stats.spread_c,
        threshold=50.0,
        unit="°C",
    )


def _check_axial_displacement(db, gt: GasTurbine, latest: OperationReading) -> None:
    if abs(latest.axial_displacement_mm) < 0.8:
        return
    level = AlertLevel.WARNING if abs(latest.axial_displacement_mm) < 1.2 else AlertLevel.CRITICAL
    emit_alert(
        db,
        gas_turbine_id=gt.id,
        cc_unit_id=None,
        category="AXIAL",
        level=level,
        title=f"{gt.code} 轴位移 {latest.axial_displacement_mm:.2f} mm 超阈",
        description="推力轴承位移异常，必要时立即停机",
        measured_value=latest.axial_displacement_mm,
        threshold=0.8,
        unit="mm",
    )


def degradation_daily_job() -> None:
    """每日凌晨 2 点：为每台 RUNNING 燃机汇总过去 7 天退化率"""
    db = SessionLocal()
    try:
        running = db.scalars(
            select(GasTurbine).where(GasTurbine.status == EquipmentStatus.RUNNING)
        ).all()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=7)
        for gt in running:
            try:
                rows = (
                    db.query(PerformanceCalculation)
                    .filter(
                        PerformanceCalculation.gas_turbine_id == gt.id,
                        PerformanceCalculation.calc_time >= window_start,
                    )
                    .all()
                )
                if len(rows) < 24:  # 至少 24 个样本才有意义
                    continue
                avg_pow_dev = sum(r.power_deviation_pct for r in rows) / len(rows)
                avg_hr_dev = sum(r.heat_rate_deviation_pct for r in rows) / len(rows)
                # 假设每个样本代表 0.25h（15min 窗口）
                running_hours = len(rows) * 0.25
                deg_rate = (avg_pow_dev / running_hours) * 1000.0 if running_hours > 0 else 0.0

                rec = DegradationRecord(
                    record_no=next_degradation_no(db, window_start.date()),
                    gas_turbine_id=gt.id,
                    period_start=window_start.date(),
                    period_end=now.date(),
                    avg_power_deviation_pct=round(avg_pow_dev, 3),
                    avg_heat_rate_deviation_pct=round(avg_hr_dev, 3),
                    degradation_rate_pct_per_1000h=round(deg_rate, 3),
                    running_hours=round(running_hours, 1),
                    wash_recommended=pc.wash_recommended(avg_pow_dev, running_hours),
                    overhaul_recommended=pc.overhaul_recommended(avg_pow_dev, running_hours),
                )
                db.add(rec)
                db.commit()
            except Exception:
                logger.exception("degradation_daily_job failed for %s", gt.code)
    finally:
        db.close()


# ============================================================================
# Lifecycle
# ============================================================================

def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    s = get_settings()
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(
        perf_calc_job,
        IntervalTrigger(minutes=s.perf_calc_interval_minutes),
        id="perf_calc_job",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    sched.add_job(
        health_check_job,
        IntervalTrigger(minutes=s.vibration_check_interval_minutes),
        id="health_check_job",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    sched.add_job(
        degradation_daily_job,
        CronTrigger(hour=s.degradation_daily_hour, minute=0),
        id="degradation_daily_job",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    sched.start()
    _scheduler = sched
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
