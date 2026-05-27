"""APScheduler 3 类作业的逻辑单测 (直接调用 job 函数，不启动 scheduler)。

跨系统 push 调用会在测试环境无法到达远端 → 实现侧已用 try/except 吞掉。
此处只验证：作业本身能跑通、副作用（告警 / 退化记录）正确写入 DB。
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.models.alert import Alert, AlertLevel, AlertStatus
from app.models.performance import PerformanceCalculation
from app.models.reading import OperationReading
from app.services import scheduler as sched
from app.services.alerting import emit_alert


def _gt_id(client, auth):
    return client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]


# ============================================================================
# 阻断跨系统真实调用 (整文件级 monkeypatch)
# ============================================================================

@patch("app.services.scheduler.push_defect_to_inspection", lambda **kw: True)
@patch("app.services.scheduler.push_safety_event", lambda **kw: True)
@patch("app.services.scheduler.push_performance_snapshot_to_fuel_metering", lambda **kw: True)
class TestSchedulerJobs:

    def test_perf_calc_job_with_data(self, client, auth, seed_window_readings):
        gt_id = _gt_id(client, auth)
        seed_window_readings(gt_id, minutes=15)
        # 跑一次：应产生 PerformanceCalculation 记录
        sched.perf_calc_job()
        # 验证：取回 calculations
        from tests.conftest import TestingSessionLocal
        with TestingSessionLocal() as db:
            calcs = db.query(PerformanceCalculation).all()
            assert len(calcs) == 1
            assert calcs[0].corrected_power_mw > 0

    def test_perf_calc_job_no_data_no_error(self, client, auth):
        # 没有 readings → 不应 raise
        sched.perf_calc_job()

    def test_health_check_vibration_alert(self, client, auth, db_session):
        gt_id = _gt_id(client, auth)
        db_session.add(OperationReading(
            gas_turbine_id=gt_id,
            timestamp=datetime.now(timezone.utc),
            vibration_mm_s=8.5,  # D 区
            gross_power_mw=290, fuel_flow_nm3_h=60000,
        ))
        db_session.commit()
        sched.health_check_job()
        a = db_session.query(Alert).filter(Alert.category == "VIBRATION").first()
        assert a is not None
        assert a.level == AlertLevel.CRITICAL

    def test_health_check_vibration_dedups(self, client, auth, db_session):
        gt_id = _gt_id(client, auth)
        db_session.add(OperationReading(
            gas_turbine_id=gt_id, timestamp=datetime.now(timezone.utc),
            vibration_mm_s=6.0,  # C 区
            gross_power_mw=290, fuel_flow_nm3_h=60000,
        ))
        db_session.commit()
        sched.health_check_job()
        sched.health_check_job()  # 第二次
        count = (
            db_session.query(Alert)
            .filter(Alert.category == "VIBRATION", Alert.status == AlertStatus.OPEN)
            .count()
        )
        assert count == 1  # 去重生效

    def test_health_check_no_alert_in_a_zone(self, client, auth, db_session):
        gt_id = _gt_id(client, auth)
        db_session.add(OperationReading(
            gas_turbine_id=gt_id, timestamp=datetime.now(timezone.utc),
            vibration_mm_s=1.5, gross_power_mw=290, fuel_flow_nm3_h=60000,
        ))
        db_session.commit()
        sched.health_check_job()
        assert db_session.query(Alert).filter(Alert.category == "VIBRATION").count() == 0

    def test_health_check_egt_spread_alert(self, client, auth, db_session):
        gt_id = _gt_id(client, auth)
        db_session.add(OperationReading(
            gas_turbine_id=gt_id, timestamp=datetime.now(timezone.utc),
            egt_t1_c=680, egt_t2_c=600, egt_t3_c=600,
            egt_t4_c=600, egt_t5_c=600, egt_t6_c=600,
            gross_power_mw=290, fuel_flow_nm3_h=60000,
        ))
        db_session.commit()
        sched.health_check_job()
        a = db_session.query(Alert).filter(Alert.category == "EGT_SPREAD").first()
        assert a is not None

    def test_health_check_axial_displacement(self, client, auth, db_session):
        gt_id = _gt_id(client, auth)
        db_session.add(OperationReading(
            gas_turbine_id=gt_id, timestamp=datetime.now(timezone.utc),
            axial_displacement_mm=1.5,  # CRITICAL
            gross_power_mw=290, fuel_flow_nm3_h=60000,
        ))
        db_session.commit()
        sched.health_check_job()
        a = db_session.query(Alert).filter(Alert.category == "AXIAL").first()
        assert a is not None
        assert a.level == AlertLevel.CRITICAL

    def test_degradation_daily_no_samples(self, client, auth):
        # 不足 24 条样本 → 跳过
        sched.degradation_daily_job()  # 不抛即过


class TestSchedulerLifecycle:
    def test_start_and_shutdown(self):
        s = sched.start_scheduler()
        assert s is not None and s.running
        sched.shutdown_scheduler()


class TestAlertingDedup:
    def test_emit_alert_first_time(self, db_session, client, auth):
        gt_id = _gt_id(client, auth)
        a = emit_alert(
            db_session, gas_turbine_id=gt_id, cc_unit_id=None,
            category="VIBRATION", level=AlertLevel.WARNING,
            title="t1", measured_value=5.0, threshold=4.5, unit="mm/s",
        )
        assert a.id is not None
        assert a.alert_no.startswith("AL-")

    def test_emit_alert_second_time_dedups(self, db_session, client, auth):
        gt_id = _gt_id(client, auth)
        a1 = emit_alert(
            db_session, gas_turbine_id=gt_id, cc_unit_id=None,
            category="VIBRATION", level=AlertLevel.WARNING,
            title="t1", measured_value=5.0, threshold=4.5, unit="mm/s",
        )
        a2 = emit_alert(
            db_session, gas_turbine_id=gt_id, cc_unit_id=None,
            category="VIBRATION", level=AlertLevel.CRITICAL,  # 升级 level
            title="t1-升级", measured_value=8.0, threshold=4.5, unit="mm/s",
        )
        assert a2.id == a1.id  # 同一条
        assert a2.level == AlertLevel.CRITICAL  # 已升级
        assert a2.measured_value == 8.0  # 已刷新
