from datetime import date, datetime

from pydantic import BaseModel, Field


class PerformanceCalculationOut(BaseModel):
    id: int
    batch_no: str
    gas_turbine_id: int
    cc_unit_id: int | None
    calc_time: datetime
    sample_count: int
    measured_power_mw: float
    measured_heat_rate_kj_kwh: float
    measured_efficiency: float
    measured_egt_c: float
    egt_spread_c: float
    corrected_power_mw: float
    corrected_heat_rate_kj_kwh: float
    corrected_efficiency: float
    temp_correction: float
    pressure_correction: float
    humidity_correction: float
    baseline_id: int | None
    power_deviation_pct: float
    heat_rate_deviation_pct: float
    cc_total_power_mw: float | None
    cc_efficiency: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerCalcRequest(BaseModel):
    gas_turbine_id: int
    window_minutes: int = Field(default=15, ge=1, le=240)


class BaselineCreate(BaseModel):
    gas_turbine_id: int
    baseline_date: date
    baseline_type: str = "COMMISSIONING"
    load_pct: float = Field(ge=10, le=110)
    iso_corrected_power_mw: float = Field(gt=0)
    iso_corrected_heat_rate_kj_kwh: float = Field(gt=0)
    iso_corrected_efficiency: float = Field(gt=0, le=1)
    iso_corrected_egt_c: float = 600.0
    remarks: str = ""


class BaselineOut(BaselineCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DegradationOut(BaseModel):
    id: int
    record_no: str
    gas_turbine_id: int
    period_start: date
    period_end: date
    avg_power_deviation_pct: float
    avg_heat_rate_deviation_pct: float
    degradation_rate_pct_per_1000h: float
    running_hours: float
    wash_recommended: bool
    overhaul_recommended: bool
    remarks: str
    created_at: datetime

    model_config = {"from_attributes": True}
