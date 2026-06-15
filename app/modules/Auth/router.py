from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.Core.config import settings
from app.Core.database import get_session
from app.modules.Auth.schemas import LoginRequest, RefreshRequest, SessionResponse
from app.modules.Auth.service import AuthService


router = APIRouter(
   prefix="/api/v1/auth",
   tags=["auth"],
)

def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
   return AuthService(session)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=expires_in,
        httponly=True,
        samesite="none" if settings.COOKIE_SECURE else "lax",
        secure=settings.COOKIE_SECURE,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=60 * 60 * 24 * 7,
        path="/api/v1/auth/refresh",
        httponly=True,
        samesite="none" if settings.COOKIE_SECURE else "lax",
        secure=settings.COOKIE_SECURE,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
   "/login",
   response_model=SessionResponse,
   status_code=status.HTTP_200_OK,
   summary="Autenticarse con email y password — tokens se setean como cookies HTTPOnly",
)
def login(
   data: LoginRequest,
   response: Response,
   svc: AuthService = Depends(get_auth_service),
) -> SessionResponse:
   
   result = svc.login(data)
   
   _set_auth_cookies(response, result.access_token, result.refresh_token, result.expires_in)
   return SessionResponse(expires_in=result.expires_in)


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
   "/refresh",
   response_model=SessionResponse,
   status_code=status.HTTP_200_OK,
   summary="Rotar el refresh token usando la cookie — emite un nuevo par de cookies",
)
def refresh(
   request: Request,
   response: Response,
   svc: AuthService = Depends(get_auth_service),
) -> SessionResponse:
   refresh_token = request.cookies.get("refresh_token")
   if not refresh_token:
      raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado",
      )
   result = svc.refresh(RefreshRequest(refresh_token=refresh_token))
   _set_auth_cookies(response, result.access_token, result.refresh_token, result.expires_in)
   return SessionResponse(expires_in=result.expires_in)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
   "/logout",
   status_code=status.HTTP_204_NO_CONTENT,
   summary="Revocar el refresh token y borrar las cookies de sesión",
)
def logout(
   request: Request,
   response: Response,
   svc: AuthService = Depends(get_auth_service),
) -> None:
   refresh_token = request.cookies.get("refresh_token")
   if refresh_token:
      svc.logout(RefreshRequest(refresh_token=refresh_token))
   response.delete_cookie("access_token")
   response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
