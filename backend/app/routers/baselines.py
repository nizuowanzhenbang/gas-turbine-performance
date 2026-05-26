from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import GasTurbine
from app.models.performance import PerformanceBaseline
from app.models.user import User, UserRole
from app.schemas.performance import BaselineCreate, BaselineOut

router = APIRouter()


@router.get("/", response_model=list[BaselineOut])
def list_baselines(
    gas_turbine_id: int | None = Query(None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PerformanceBaseline)
    if gas_turbine_id is not None:
        q = q.filter(PerformanceBaseline.gas_turbine_id == gas_turbine_id)
    return q.order_by(PerformanceBaseline.gas_turbine_id, PerformanceBaseline.load_pct).all()


@router.post("/", response_model=BaselineOut, status_code=status.HTTP_201_CREATED)
def create_baseline(
    payload: BaselineCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if not db.query(GasTurbine).get(payload.gas_turbine_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gas turbine not found")
    b = PerformanceBaseline(**payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/{baseline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_baseline(
    baseline_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    b = db.query(PerformanceBaseline).get(baseline_id)
    if not b:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Baseline not found")
    db.delete(b)
    db.commit()
