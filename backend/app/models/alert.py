from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # AL-YYYYMMDD-NNNN

    # 业务对象
    gas_turbine_id: Mapped[int | None] = mapped_column(ForeignKey("gas_turbines.id"), nullable=True)
    cc_unit_id: Mapped[int | None] = mapped_column(ForeignKey("combined_cycle_units.id"), nullable=True)

    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # VIBRATION / EGT_SPREAD / DEGRADATION / HEAT_RATE / BEARING / AXIAL / IGV / OTHER

    level: Mapped[AlertLevel] = mapped_column(String(16), nullable=False, default=AlertLevel.WARNING)
    status: Mapped[AlertStatus] = mapped_column(String(16), nullable=False, default=AlertStatus.OPEN)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    measured_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="")

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 跨系统出库
    pushed_to_inspection: Mapped[bool] = mapped_column(default=False)
    pushed_to_safety: Mapped[bool] = mapped_column(default=False)
    push_remarks: Mapped[str] = mapped_column(String(500), nullable=False, default="")
