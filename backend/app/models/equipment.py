from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EquipmentStatus(str, Enum):
    RUNNING = "RUNNING"
    STANDBY = "STANDBY"
    MAINTENANCE = "MAINTENANCE"
    OUTAGE = "OUTAGE"
    DECOMMISSIONED = "DECOMMISSIONED"


class GasTurbine(Base):
    """燃机台账：型号、铭牌出力、ISO 工况基准"""
    __tablename__ = "gas_turbines"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)  # GT-01
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # 9F.04, M701F4
    serial_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rated_power_mw: Mapped[float] = mapped_column(Float, nullable=False)            # MW
    rated_heat_rate_kj_kwh: Mapped[float] = mapped_column(Float, nullable=False)    # kJ/kWh
    rated_efficiency: Mapped[float] = mapped_column(Float, nullable=False)          # 0-1
    iso_ambient_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    iso_ambient_pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False, default=101.325)
    iso_relative_humidity: Mapped[float] = mapped_column(Float, nullable=False, default=0.60)
    rated_egt_c: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    rated_speed_rpm: Mapped[float] = mapped_column(Float, nullable=False, default=3000.0)
    status: Mapped[EquipmentStatus] = mapped_column(String(32), nullable=False, default=EquipmentStatus.STANDBY)
    location: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    remarks: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HRSGUnit(Base):
    """余热锅炉 (Heat Recovery Steam Generator)"""
    __tablename__ = "hrsg_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)  # HRSG-01
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    rated_hp_steam_t_h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 高压蒸汽 t/h
    rated_hp_pressure_mpa: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rated_hp_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rated_ip_steam_t_h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rated_lp_steam_t_h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rated_efficiency: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    status: Mapped[EquipmentStatus] = mapped_column(String(32), nullable=False, default=EquipmentStatus.STANDBY)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SteamTurbine(Base):
    """汽轮机"""
    __tablename__ = "steam_turbines"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)  # ST-01
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    rated_power_mw: Mapped[float] = mapped_column(Float, nullable=False)
    rated_efficiency: Mapped[float] = mapped_column(Float, nullable=False, default=0.42)
    rated_speed_rpm: Mapped[float] = mapped_column(Float, nullable=False, default=3000.0)
    status: Mapped[EquipmentStatus] = mapped_column(String(32), nullable=False, default=EquipmentStatus.STANDBY)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CombinedCycleUnit(Base):
    """联合循环单元（GT + HRSG + ST）"""
    __tablename__ = "combined_cycle_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)  # CC-01
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    configuration: Mapped[str] = mapped_column(String(32), nullable=False, default="1-1-1")  # 1GT-1HRSG-1ST
    gas_turbine_id: Mapped[int] = mapped_column(ForeignKey("gas_turbines.id"), nullable=False)
    hrsg_id: Mapped[int] = mapped_column(ForeignKey("hrsg_units.id"), nullable=False)
    steam_turbine_id: Mapped[int] = mapped_column(ForeignKey("steam_turbines.id"), nullable=False)
    rated_total_power_mw: Mapped[float] = mapped_column(Float, nullable=False)
    rated_cc_efficiency: Mapped[float] = mapped_column(Float, nullable=False, default=0.58)
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[EquipmentStatus] = mapped_column(String(32), nullable=False, default=EquipmentStatus.STANDBY)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
