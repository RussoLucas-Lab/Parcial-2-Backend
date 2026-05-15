import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.Core.config import settings
from app.Core.security import create_access_token, verify_password
from app.modules.Auth.unit_of_work import AuthUnitOfWork
from app.modules.Auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.modules.Usuario.model import UsuarioRol


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_role_codes(self, usuario_id: int) -> list[str]:
        rows = self._session.exec(
            select(UsuarioRol.rol_codigo).where(UsuarioRol.usuario_id == usuario_id)
        ).all()
        return list(rows)

    def _build_token_response(self, usuario_id: int, uow: AuthUnitOfWork) -> TokenResponse:
        roles = self._get_role_codes(usuario_id)
        access_token = create_access_token({"sub": str(usuario_id), "roles": roles})

        raw_refresh = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        uow.tokens.create(usuario_id, token_hash, expires_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> TokenResponse:
        with AuthUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_email(data.email)

            if not user or not verify_password(data.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            result = self._build_token_response(user.id, uow)

        return result

    def refresh(self, data: RefreshRequest) -> TokenResponse:
        with AuthUnitOfWork(self._session) as uow:
            token_hash = _hash_token(data.refresh_token)
            stored = uow.tokens.get_by_hash(token_hash)

            if not stored:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido",
                )

            now = datetime.now(timezone.utc)
            if stored.expires_at.replace(tzinfo=timezone.utc) < now or stored.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expirado o revocado",
                )

            uow.tokens.revoke(stored)
            result = self._build_token_response(stored.usuario_id, uow)

        return result

    def logout(self, data: RefreshRequest) -> None:
        with AuthUnitOfWork(self._session) as uow:
            token_hash = _hash_token(data.refresh_token)
            stored = uow.tokens.get_by_hash(token_hash)

            if stored and stored.revoked_at is None:
                uow.tokens.revoke(stored)
