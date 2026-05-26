from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.alert import Alert, AlertLevel, AlertStatus
from app.models.equipment import CombinedCycleUnit, EquipmentStatus, GasTurbine, HRSGUnit, SteamTurbine
from app.models.performance import PerformanceCalculation
from app.models.reading import OperationReading
from app.models.user import User

router = APIRouter()


@router.get("/summary")
def summary(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    gt_total = db.query(func.count(GasTurbine.id)).scalar() or 0
    gt_running = db.query(func.count(GasTurbine.id)).filter(GasTurbine.status == EquipmentStatus.RUNNING).scalar() or 0
    cc_total = db.query(func.count(CombinedCycleUnit.id)).scalar() or 0
    hrsg_total = db.query(func.count(HRSGUnit.id)).scalar() or 0
    st_total = db.query(func.count(SteamTurbine.id)).scalar() or 0

    open_alerts = db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.OPEN).scalar() or 0
    critical_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status == AlertStatus.OPEN, Alert.level == AlertLevel.CRITICAL
    ).scalar() or 0

    last_day = datetime.now(timezone.utc) - timedelta(hours=24)
    total_gen_mwh = db.query(func.coalesce(func.sum(OperationReading.gross_power_mw), 0.0)).filter(
        OperationReading.timestamp >= last_day
    ).scalar() or 0.0
    # 简化: 把读数视为 1 分钟一条，因此 sum / 60 = MWh
    total_gen_mwh = float(total_gen_mwh) / 60.0

    return {
        "gas_turbines": {"total": gt_total, "running": gt_running},
        "combined_cycle_units": cc_total,
        "hrsg": hrsg_total,
        "steam_turbines": st_total,
        "alerts": {"open": open_alerts, "critical": critical_alerts},
        "generation_24h_mwh": round(total_gen_mwh, 1),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance-trend")
def performance_trend(
    gas_turbine_id: int,
    days: int = 14,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(PerformanceCalculation)
        .filter(
            PerformanceCalculation.gas_turbine_id == gas_turbine_id,
            PerformanceCalculation.calc_time >= since,
        )
        .order_by(PerformanceCalculation.calc_time.asc())
        .all()
    )
    return {
        "gas_turbine_id": gas_turbine_id,
        "series": [
            {
                "t": r.calc_time.isoformat(),
                "corrected_power_mw": round(r.corrected_power_mw, 2),
                "corrected_heat_rate_kj_kwh": round(r.corrected_heat_rate_kj_kwh, 1),
                "corrected_efficiency": round(r.corrected_efficiency, 4),
                "power_deviation_pct": round(r.power_deviation_pct, 3),
                "egt_spread_c": round(r.egt_spread_c, 2),
            }
            for r in rows
        ],
    }
