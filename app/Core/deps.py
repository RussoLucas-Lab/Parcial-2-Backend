from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.Core.database import get_session
from app.Core.security import decode_access_token
from app.modules.Usuario.model import Usuario, UsuarioRol


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
   async def __call__(self, request: Request) -> str | None:
      token = request.cookies.get("access_token")
      if not token:
            if self.auto_error:
               raise HTTPException(
                  status_code=status.HTTP_401_UNAUTHORIZED,
                  detail="No autenticado",
                  headers={"WWW-Authenticate": "Bearer"},
               )
            return None
      return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/token")


async def get_current_user(
   token: Annotated[str, Depends(oauth2_scheme)],
   session: Annotated[Session, Depends(get_session)],
) -> Usuario:
   credentials_exception = HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Credenciales inválidas o token expirado",
      headers={"WWW-Authenticate": "Bearer"},
   )

   payload = decode_access_token(token)
   if payload is None:
      raise credentials_exception

   user_id: str | None = payload.get("sub")
   if user_id is None:
      raise credentials_exception

   user = session.exec(
      select(Usuario)
      .where(Usuario.id == int(user_id))
      .where(Usuario.activo == True)
   ).first()

   if user is None:
      raise credentials_exception

   return user


async def get_current_active_user(
   current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
   if not current_user.activo:
      raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
      )
   return current_user


def require_role(allowed_roles: list[str]):
   async def role_checker(
      current_user: Annotated[Usuario, Depends(get_current_active_user)],
      session: Annotated[Session, Depends(get_session)],
   ) -> Usuario:
      roles = session.exec(
            select(UsuarioRol.rol_codigo)
            .where(UsuarioRol.usuario_id == current_user.id)
      ).all()

      if not any(r in allowed_roles for r in roles):
            raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail=f"Permisos insuficientes. Se requiere uno de: {allowed_roles}",
            )
      return current_user

   return role_checker
