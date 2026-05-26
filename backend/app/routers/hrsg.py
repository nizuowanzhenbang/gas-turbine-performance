from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import HRSGUnit
from app.models.user import User, UserRole
from app.schemas.equipment import HRSGCreate, HRSGOut

router = APIRouter()


@router.get("/", response_model=list[HRSGOut])
def list_hrsg(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(HRSGUnit).order_by(HRSGUnit.code).all()


@router.post("/", response_model=HRSGOut, status_code=status.HTTP_201_CREATED)
def create_hrsg(
    payload: HRSGCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if db.query(HRSGUnit).filter(HRSGUnit.code == payload.code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Code exists")
    h = HRSGUnit(**payload.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.get("/{hrsg_id}", response_model=HRSGOut)
def get_hrsg(hrsg_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(HRSGUnit).get(hrsg_id)
    if not h:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "HRSG not found")
    return h
