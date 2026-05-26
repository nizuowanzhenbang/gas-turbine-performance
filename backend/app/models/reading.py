from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationReading(Base):
    """燃机运行参数时序读数（每分钟级）"""
    __tablename__ = "operation_readings"
    __table_args__ = (
        Index("ix_reading_gt_time", "gas_turbine_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    gas_turbine_id: Mapped[int] = mapped_column(ForeignKey("gas_turbines.id"), nullable=False, index=True)
    cc_unit_id: Mapped[int | None] = mapped_column(ForeignKey("combined_cycle_units.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # 环境参数
    ambient_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    ambient_pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False, default=101.0)
    relative_humidity: Mapped[float] = mapped_column(Float, nullable=False, default=0.60)

    # 燃料
    fuel_flow_nm3_h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 标方/小时
    fuel_lhv_kj_nm3: Mapped[float] = mapped_column(Float, nullable=False, default=35880.0)  # 来自 gas-fuel-metering

    # 压气机
    compressor_inlet_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    compressor_inlet_pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False, default=101.0)
    compressor_outlet_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=400.0)
    compressor_outlet_pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False, default=1700.0)
    pressure_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=17.0)

    # 燃烧 / 透平
    exhaust_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    # EGT 多点温度 (热电偶 1-6 的标准差衡量散布)
    egt_t1_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    egt_t2_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    egt_t3_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    egt_t4_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    egt_t5_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    egt_t6_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    exhaust_flow_kg_s: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)

    # 出力 / 运行
    gross_power_mw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    speed_rpm: Mapped[float] = mapped_column(Float, nullable=False, default=3000.0)
    igv_angle_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 健康监测
    bearing_temp_max_c: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)
    vibration_mm_s: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)  # 速度有效值
    axial_displacement_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # HRSG / ST (联合循环)
    hp_steam_flow_t_h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hp_steam_pressure_mpa: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hp_steam_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    st_power_mw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="DCS")  # DCS / MANUAL / SIMULATED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
