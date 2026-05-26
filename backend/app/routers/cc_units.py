from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.equipment import CombinedCycleUnit, GasTurbine, HRSGUnit, SteamTurbine
from app.models.user import User, UserRole
from app.schemas.equipment import CCUnitCreate, CCUnitOut

router = APIRouter()


@router.get("/", response_model=list[CCUnitOut])
def list_cc(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(CombinedCycleUnit).order_by(CombinedCycleUnit.code).all()


@router.post("/", response_model=CCUnitOut, status_code=status.HTTP_201_CREATED)
def create_cc(
    payload: CCUnitCreate,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG)),
    db: Session = Depends(get_db),
):
    if db.query(CombinedCycleUnit).filter(CombinedCycleUnit.code == payload.code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Code exists")
    for model, fid, label in [
        (GasTurbine, payload.gas_turbine_id, "gas_turbine"),
        (HRSGUnit, payload.hrsg_id, "hrsg"),
        (SteamTurbine, payload.steam_turbine_id, "steam_turbine"),
    ]:
        if not db.query(model).get(fid):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} not found")
    cc = CombinedCycleUnit(**payload.model_dump())
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


@router.get("/{cc_id}", response_model=CCUnitOut)
def get_cc(cc_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cc = db.query(CombinedCycleUnit).get(cc_id)
    if not cc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CC unit not found")
    return cc
