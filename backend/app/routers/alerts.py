from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.alert import Alert, AlertLevel, AlertStatus
from app.models.user import User, UserRole
from app.schemas.alert import AlertAckRequest, AlertOut, AlertResolveRequest

router = APIRouter()


@router.get("/", response_model=list[AlertOut])
def list_alerts(
    status_: AlertStatus | None = Query(None, alias="status"),
    level: AlertLevel | None = Query(None),
    gas_turbine_id: int | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if status_ is not None:
        q = q.filter(Alert.status == status_)
    if level is not None:
        q = q.filter(Alert.level == level)
    if gas_turbine_id is not None:
        q = q.filter(Alert.gas_turbine_id == gas_turbine_id)
    return q.order_by(Alert.triggered_at.desc()).limit(limit).all()


@router.post("/{alert_id}/ack", response_model=AlertOut)
def ack_alert(
    alert_id: int,
    payload: AlertAckRequest,
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.PERFORMANCE_ENG, UserRole.MAINTENANCE)),
    db: Session = Depends(get_db),
):
    a = db.query(Alert).get(alert_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    if a.status != AlertStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Alert not OPEN")
    a.status = AlertStatus.ACKNOWLEDGED
    a.acknowledged_at = datetime.now(timezone.utc)
    a.acknowledged_by = user.username
    if payload.remarks:
        a.push_remarks = (a.push_remarks + " | " + payload.remarks).strip(" |")
    db.commit()
    db.refresh(a)
    return a


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(
    alert_id: int,
    payload: AlertResolveRequest,
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.PERFORMANCE_ENG, UserRole.MAINTENANCE)),
    db: Session = Depends(get_db),
):
    a = db.query(Alert).get(alert_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    if a.status in (AlertStatus.RESOLVED, AlertStatus.SUPPRESSED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Alert already closed")
    a.status = AlertStatus.RESOLVED
    a.resolved_at = datetime.now(timezone.utc)
    a.resolved_by = user.username
    if payload.remarks:
        a.push_remarks = (a.push_remarks + " | " + payload.remarks).strip(" |")
    db.commit()
    db.refresh(a)
    return a
