from datetime import datetime

from pydantic import BaseModel

from app.models.alert import AlertLevel, AlertStatus


class AlertOut(BaseModel):
    id: int
    alert_no: str
    gas_turbine_id: int | None
    cc_unit_id: int | None
    category: str
    level: AlertLevel
    status: AlertStatus
    title: str
    description: str
    measured_value: float | None
    threshold: float | None
    unit: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    pushed_to_inspection: bool
    pushed_to_safety: bool
    push_remarks: str

    model_config = {"from_attributes": True}


class AlertAckRequest(BaseModel):
    remarks: str = ""


class AlertResolveRequest(BaseModel):
    remarks: str = ""
