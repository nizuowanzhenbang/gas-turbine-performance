"""把若干 OperationReading 平均化后跑性能计算并持久化结果。"""
from datetime import datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import GasTurbine
from app.models.performance import PerformanceBaseline, PerformanceCalculation
from app.models.reading import OperationReading
from app.services import performance_calc as pc
from app.utils.numbering import next_perf_batch_no


def _avg(values):
    values = list(values)
    return mean(values) if values else 0.0


def _select_baseline(
    db: Session, gas_turbine_id: int, load_pct: float
) -> PerformanceBaseline | None:
    stmt = select(PerformanceBaseline).where(
        PerformanceBaseline.gas_turbine_id == gas_turbine_id
    ).order_by(PerformanceBaseline.baseline_date.desc())
    candidates = db.scalars(stmt).all()
    if not candidates:
        return None
    return min(candidates, key=lambda b: abs(b.load_pct - load_pct))


def compute_for_window(
    db: Session,
    gas_turbine_id: int,
    window_minutes: int = 15,
    *,
    end_time: datetime | None = None,
) -> PerformanceCalculation | None:
    """取 [end-window, end] 内的运行数据，加权计算性能并写入一条记录。

    若窗口内无数据或燃机停机（gross_power < 1 MW），返回 None。
    """
    end_time = end_time or datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=window_minutes)

    gt = db.query(GasTurbine).get(gas_turbine_id)
    if not gt:
        return None

    rows = (
        db.query(OperationReading)
        .filter(
            OperationReading.gas_turbine_id == gas_turbine_id,
            OperationReading.timestamp >= start_time,
            OperationReading.timestamp <= end_time,
        )
        .order_by(OperationReading.timestamp.asc())
        .all()
    )
    if not rows:
        return None

    avg_power = _avg(r.gross_power_mw for r in rows)
    if avg_power < 1.0:
        return None  # 燃机未运行

    avg_fuel_flow = _avg(r.fuel_flow_nm3_h for r in rows)
    avg_lhv = _avg(r.fuel_lhv_kj_nm3 for r in rows)
    avg_temp = _avg(r.ambient_temp_c for r in rows)
    avg_press = _avg(r.ambient_pressure_kpa for r in rows)
    avg_rh = _avg(r.relative_humidity for r in rows)
    avg_egt = _avg(r.exhaust_temp_c for r in rows)
    avg_st_power = _avg(r.st_power_mw for r in rows)

    # EGT spread: 取最后一条样本的 6 个 TC 即可（spread 是空间分布，不需时间平均）
    last = rows[-1]
    egt_stats = pc.egt_statistics(
        [last.egt_t1_c, last.egt_t2_c, last.egt_t3_c, last.egt_t4_c, last.egt_t5_c, last.egt_t6_c]
    )

    iso_result = pc.iso_correct(
        measured_power_mw=avg_power,
        fuel_flow_nm3_h=avg_fuel_flow,
        fuel_lhv_kj_nm3=avg_lhv,
        ambient_temp_c=avg_temp,
        ambient_pressure_kpa=avg_press,
        relative_humidity=avg_rh,
    )

    load_pct = avg_power / gt.rated_power_mw * 100.0
    baseline = _select_baseline(db, gas_turbine_id, load_pct)
    power_dev = 0.0
    hr_dev = 0.0
    if baseline:
        power_dev = (baseline.iso_corrected_power_mw - iso_result.corrected_power_mw) / baseline.iso_corrected_power_mw * 100.0
        hr_dev = (iso_result.corrected_heat_rate_kj_kwh - baseline.iso_corrected_heat_rate_kj_kwh) / baseline.iso_corrected_heat_rate_kj_kwh * 100.0

    cc_total = None
    cc_eff = None
    if avg_st_power > 1.0 and avg_fuel_flow > 0 and avg_lhv > 0:
        q_in = pc.fuel_energy_input_kw(avg_fuel_flow, avg_lhv)
        cc_total = avg_power + avg_st_power
        cc_eff = pc.combined_cycle_efficiency(avg_power, avg_st_power, q_in)

    record = PerformanceCalculation(
        batch_no=next_perf_batch_no(db, end_time),
        gas_turbine_id=gas_turbine_id,
        cc_unit_id=last.cc_unit_id,
        calc_time=end_time,
        sample_count=len(rows),
        measured_power_mw=iso_result.measured_power_mw,
        measured_heat_rate_kj_kwh=iso_result.measured_heat_rate_kj_kwh,
        measured_efficiency=iso_result.measured_efficiency,
        measured_egt_c=avg_egt,
        egt_spread_c=egt_stats.spread_c,
        corrected_power_mw=iso_result.corrected_power_mw,
        corrected_heat_rate_kj_kwh=iso_result.corrected_heat_rate_kj_kwh,
        corrected_efficiency=iso_result.corrected_efficiency,
        temp_correction=iso_result.temp_correction,
        pressure_correction=iso_result.pressure_correction,
        humidity_correction=iso_result.humidity_correction,
        baseline_id=baseline.id if baseline else None,
        power_deviation_pct=power_dev,
        heat_rate_deviation_pct=hr_dev,
        cc_total_power_mw=cc_total,
        cc_efficiency=cc_eff,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
