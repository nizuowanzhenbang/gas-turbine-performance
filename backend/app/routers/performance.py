from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.performance import DegradationRecord, PerformanceCalculation
from app.models.user import User, UserRole
from app.schemas.performance import DegradationOut, PerformanceCalculationOut, TriggerCalcRequest
from app.services.perf_engine import compute_for_window

router = APIRouter()


@router.get("/", response_model=list[PerformanceCalculationOut])
def list_calculations(
    gas_turbine_id: int | None = Query(None),
    days: int = Query(7, ge=1, le=180),
    limit: int = Query(200, ge=1, le=2000),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PerformanceCalculation)
    if gas_turbine_id is not None:
        q = q.filter(PerformanceCalculation.gas_turbine_id == gas_turbine_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return q.filter(PerformanceCalculation.calc_time >= since).order_by(PerformanceCalculation.calc_time.desc()).limit(limit).all()


@router.post("/calculate", response_model=PerformanceCalculationOut, status_code=status.HTTP_201_CREATED)
def trigger_calculation(
    req: TriggerCalcRequest,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
):
    record = compute_for_window(db, req.gas_turbine_id, req.window_minutes)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No data or turbine offline in window")
    return record


@router.get("/degradation/", response_model=list[DegradationOut])
def list_degradation(
    gas_turbine_id: int | None = Query(None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DegradationRecord)
    if gas_turbine_id is not None:
        q = q.filter(DegradationRecord.gas_turbine_id == gas_turbine_id)
    return q.order_by(DegradationRecord.period_end.desc()).all()
