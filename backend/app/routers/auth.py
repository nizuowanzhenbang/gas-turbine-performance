from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.username, user.role),
        role=user.role,
        full_name=user.full_name,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)):
    return user
