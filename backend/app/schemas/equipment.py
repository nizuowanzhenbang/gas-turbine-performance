from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.equipment import EquipmentStatus


class GasTurbineBase(BaseModel):
    code: str = Field(pattern=r"^GT-\d{2,3}$")
    name: str
    manufacturer: str = ""
    model: str = ""
    serial_no: str = ""
    commissioning_date: date | None = None
    rated_power_mw: float = Field(gt=0)
    rated_heat_rate_kj_kwh: float = Field(gt=0)
    rated_efficiency: float = Field(gt=0, le=1)
    iso_ambient_temp_c: float = 15.0
    iso_ambient_pressure_kpa: float = 101.325
    iso_relative_humidity: float = 0.60
    rated_egt_c: float = 600.0
    rated_speed_rpm: float = 3000.0
    status: EquipmentStatus = EquipmentStatus.STANDBY
    location: str = ""
    remarks: str = ""


class GasTurbineCreate(GasTurbineBase):
    pass


class GasTurbineUpdate(BaseModel):
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_no: str | None = None
    commissioning_date: date | None = None
    rated_power_mw: float | None = None
    rated_heat_rate_kj_kwh: float | None = None
    rated_efficiency: float | None = None
    status: EquipmentStatus | None = None
    location: str | None = None
    remarks: str | None = None


class GasTurbineOut(GasTurbineBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HRSGBase(BaseModel):
    code: str = Field(pattern=r"^HRSG-\d{2,3}$")
    name: str
    manufacturer: str = ""
    model: str = ""
    rated_hp_steam_t_h: float = 0.0
    rated_hp_pressure_mpa: float = 0.0
    rated_hp_temp_c: float = 0.0
    rated_ip_steam_t_h: float = 0.0
    rated_lp_steam_t_h: float = 0.0
    rated_efficiency: float = 0.85
    status: EquipmentStatus = EquipmentStatus.STANDBY


class HRSGCreate(HRSGBase):
    pass


class HRSGOut(HRSGBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SteamTurbineBase(BaseModel):
    code: str = Field(pattern=r"^ST-\d{2,3}$")
    name: str
    manufacturer: str = ""
    model: str = ""
    rated_power_mw: float = Field(gt=0)
    rated_efficiency: float = 0.42
    rated_speed_rpm: float = 3000.0
    status: EquipmentStatus = EquipmentStatus.STANDBY


class SteamTurbineCreate(SteamTurbineBase):
    pass


class SteamTurbineOut(SteamTurbineBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CCUnitBase(BaseModel):
    code: str = Field(pattern=r"^CC-\d{2,3}$")
    name: str
    configuration: str = "1-1-1"
    gas_turbine_id: int
    hrsg_id: int
    steam_turbine_id: int
    rated_total_power_mw: float = Field(gt=0)
    rated_cc_efficiency: float = 0.58
    commissioning_date: date | None = None
    status: EquipmentStatus = EquipmentStatus.STANDBY


class CCUnitCreate(CCUnitBase):
    pass


class CCUnitOut(CCUnitBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
