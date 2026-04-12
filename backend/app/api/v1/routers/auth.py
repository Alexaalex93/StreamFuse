from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_current_user, get_db
from app.api.v1.schemas.auth import AuthStatusResponse, ChangePasswordRequest, LoginRequest, LoginResponse
from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_app_settings),
) -> LoginResponse:
    service = AuthService(AppSettingRepository(db), app_settings)
    auth = service.authenticate(payload.username, payload.password)
    if auth is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token, expires_epoch = auth
    return LoginResponse(
        access_token=token,
        expires_at=datetime.fromtimestamp(expires_epoch, tz=timezone.utc),
        user_name=service.current_username(),
    )


@router.get("/me", response_model=AuthStatusResponse)
def auth_me(current_user: str = Depends(get_current_user)) -> AuthStatusResponse:
    return AuthStatusResponse(user_name=current_user, authenticated=True)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_app_settings),
) -> dict[str, bool | str]:
    service = AuthService(AppSettingRepository(db), app_settings)
    ok = service.change_password(
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    return {"ok": True, "user_name": current_user}
