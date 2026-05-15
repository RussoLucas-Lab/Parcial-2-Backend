from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.Core.database import get_session
from app.modules.Auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.modules.Auth.service import AuthService


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


def get_auth_service(
    session: Session = Depends(get_session),
) -> AuthService:
    return AuthService(session)

## REFACTOR COOKIES


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticarse con email y password, obtiene access + refresh token",
)
def login(
    data: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return svc.login(data)


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotar el refresh token y obtener un nuevo par de tokens",
)
def refresh(
    data: RefreshRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return svc.refresh(data)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revocar el refresh token (cierre de sesión)",
)
def logout(
    data: RefreshRequest,
    svc: AuthService = Depends(get_auth_service),
) -> None:
    svc.logout(data)
