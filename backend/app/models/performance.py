from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerformanceBaseline(Base):
    """性能基准曲线（出厂或新机大修后建立）

    存按工况分组的基准点；后续运行修正后与之比对得退化率。
    """
    __tablename__ = "performance_baselines"
    __table_args__ = (
        Index("ix_baseline_gt_load", "gas_turbine_id", "load_pct"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    gas_turbine_id: Mapped[int] = mapped_column(ForeignKey("gas_turbines.id"), nullable=False)
    baseline_date: Mapped[date] = mapped_column(Date, nullable=False)
    baseline_type: Mapped[str] = mapped_column(String(32), nullable=False, default="COMMISSIONING")
    # COMMISSIONING / POST_OVERHAUL / POST_WASH

    load_pct: Mapped[float] = mapped_column(Float, nullable=False)  # 50/75/100
    iso_corrected_power_mw: Mapped[float] = mapped_column(Float, nullable=False)
    iso_corrected_heat_rate_kj_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    iso_corrected_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    iso_corrected_egt_c: Mapped[float] = mapped_column(Float, nullable=False)

    remarks: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PerformanceCalculation(Base):
    """每次性能计算的结果快照（来源于若干 OperationReading 的平均）"""
    __tablename__ = "performance_calculations"
    __table_args__ = (
        Index("ix_perf_gt_time", "gas_turbine_id", "calc_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # PERF-YYYYMMDD-NNNN
    gas_turbine_id: Mapped[int] = mapped_column(ForeignKey("gas_turbines.id"), nullable=False)
    cc_unit_id: Mapped[int | None] = mapped_column(ForeignKey("combined_cycle_units.id"), nullable=True)
    calc_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(default=1)

    # 实测
    measured_power_mw: Mapped[float] = mapped_column(Float, nullable=False)
    measured_heat_rate_kj_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    measured_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    measured_egt_c: Mapped[float] = mapped_column(Float, nullable=False)
    egt_spread_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ISO 修正后
    corrected_power_mw: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_heat_rate_kj_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_efficiency: Mapped[float] = mapped_column(Float, nullable=False)

    # 修正系数明细（便于审查）
    temp_correction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    pressure_correction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    humidity_correction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # 与基准对比
    baseline_id: Mapped[int | None] = mapped_column(ForeignKey("performance_baselines.id"), nullable=True)
    power_deviation_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    heat_rate_deviation_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 联合循环（如有）
    cc_total_power_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    cc_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DegradationRecord(Base):
    """月度性能退化记录"""
    __tablename__ = "degradation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # DEG-YYYYMM-NN
    gas_turbine_id: Mapped[int] = mapped_column(ForeignKey("gas_turbines.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    avg_power_deviation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    avg_heat_rate_deviation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    degradation_rate_pct_per_1000h: Mapped[float] = mapped_column(Float, nullable=False)
    running_hours: Mapped[float] = mapped_column(Float, nullable=False)
    wash_recommended: Mapped[bool] = mapped_column(default=False)
    overhaul_recommended: Mapped[bool] = mapped_column(default=False)
    remarks: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
