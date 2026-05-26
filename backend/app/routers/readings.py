from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import GasTurbine
from app.models.reading import OperationReading
from app.models.user import User, UserRole
from app.schemas.reading import OperationReadingCreate, OperationReadingOut

router = APIRouter()


@router.get("/", response_model=list[OperationReadingOut])
def list_readings(
    gas_turbine_id: int | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(500, ge=1, le=5000),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(OperationReading)
    if gas_turbine_id is not None:
        q = q.filter(OperationReading.gas_turbine_id == gas_turbine_id)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = q.filter(OperationReading.timestamp >= since).order_by(OperationReading.timestamp.desc()).limit(limit)
    return q.all()


@router.post("/", response_model=OperationReadingOut, status_code=status.HTTP_201_CREATED)
def create_reading(
    payload: OperationReadingCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if not db.query(GasTurbine).get(payload.gas_turbine_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gas turbine not found")
    r = OperationReading(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def batch_create_readings(
    payloads: list[OperationReadingCreate],
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    objs = [OperationReading(**p.model_dump()) for p in payloads]
    db.bulk_save_objects(objs)
    db.commit()
    return {"inserted": len(objs)}
