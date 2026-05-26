from datetime import datetime

from pydantic import BaseModel, Field


class OperationReadingCreate(BaseModel):
    gas_turbine_id: int
    cc_unit_id: int | None = None
    timestamp: datetime

    ambient_temp_c: float = 20.0
    ambient_pressure_kpa: float = 101.0
    relative_humidity: float = Field(default=0.60, ge=0, le=1)

    fuel_flow_nm3_h: float = 0.0
    fuel_lhv_kj_nm3: float = 35880.0

    compressor_inlet_temp_c: float = 20.0
    compressor_inlet_pressure_kpa: float = 101.0
    compressor_outlet_temp_c: float = 400.0
    compressor_outlet_pressure_kpa: float = 1700.0
    pressure_ratio: float = 17.0

    exhaust_temp_c: float = 600.0
    egt_t1_c: float = 600.0
    egt_t2_c: float = 600.0
    egt_t3_c: float = 600.0
    egt_t4_c: float = 600.0
    egt_t5_c: float = 600.0
    egt_t6_c: float = 600.0
    exhaust_flow_kg_s: float = 600.0

    gross_power_mw: float = 0.0
    speed_rpm: float = 3000.0
    igv_angle_deg: float = 0.0

    bearing_temp_max_c: float = 80.0
    vibration_mm_s: float = 2.0
    axial_displacement_mm: float = 0.0

    hp_steam_flow_t_h: float = 0.0
    hp_steam_pressure_mpa: float = 0.0
    hp_steam_temp_c: float = 0.0
    st_power_mw: float = 0.0

    source: str = "DCS"


class OperationReadingOut(OperationReadingCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
