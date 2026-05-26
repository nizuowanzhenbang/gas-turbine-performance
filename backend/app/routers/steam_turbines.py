from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import SteamTurbine
from app.models.user import User, UserRole
from app.schemas.equipment import SteamTurbineCreate, SteamTurbineOut

router = APIRouter()


@router.get("/", response_model=list[SteamTurbineOut])
def list_st(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SteamTurbine).order_by(SteamTurbine.code).all()


@router.post("/", response_model=SteamTurbineOut, status_code=status.HTTP_201_CREATED)
def create_st(
    payload: SteamTurbineCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if db.query(SteamTurbine).filter(SteamTurbine.code == payload.code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Code exists")
    s = SteamTurbine(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/{st_id}", response_model=SteamTurbineOut)
def get_st(st_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(SteamTurbine).get(st_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Steam turbine not found")
    return s
