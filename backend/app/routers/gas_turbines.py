from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import GasTurbine
from app.models.user import User, UserRole
from app.schemas.equipment import GasTurbineCreate, GasTurbineOut, GasTurbineUpdate

router = APIRouter()


@router.get("/", response_model=list[GasTurbineOut])
def list_turbines(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(GasTurbine).order_by(GasTurbine.code).all()


@router.post("/", response_model=GasTurbineOut, status_code=status.HTTP_201_CREATED)
def create_turbine(
    payload: GasTurbineCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if db.query(GasTurbine).filter(GasTurbine.code == payload.code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Code exists")
    gt = GasTurbine(**payload.model_dump())
    db.add(gt)
    db.commit()
    db.refresh(gt)
    return gt


@router.get("/{gt_id}", response_model=GasTurbineOut)
def get_turbine(gt_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gt = db.query(GasTurbine).get(gt_id)
    if not gt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gas turbine not found")
    return gt


@router.patch("/{gt_id}", response_model=GasTurbineOut)
def update_turbine(
    gt_id: int,
    payload: GasTurbineUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    gt = db.query(GasTurbine).get(gt_id)
    if not gt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gas turbine not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(gt, k, v)
    db.commit()
    db.refresh(gt)
    return gt


@router.delete("/{gt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_turbine(
    gt_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    gt = db.query(GasTurbine).get(gt_id)
    if not gt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gas turbine not found")
    db.delete(gt)
    db.commit()
