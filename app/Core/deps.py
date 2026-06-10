from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from app.Core.security import decode_access_token
from app.Core.websocket import manager as ws_manager
from app.modules.Usuario.model import Usuario
from app.modules.Usuario.unit_of_work import (
   UnitOfWork as UsuarioUnitOfWork,
   get_usuario_uow
)


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


oauth2_scheme = OAuth2PasswordBearerWithCookie(
   tokenUrl="/api/v1/auth/token"
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    uow: Annotated[
        UsuarioUnitOfWork,
        Depends(get_usuario_uow)
    ],
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

    user = uow.usuarios.get_by_id(int(user_id))

    if user is None:
        raise credentials_exception

    if not user.activo:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[
        Usuario,
        Depends(get_current_user)
    ],
) -> Usuario:

    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )

    return current_user

# Función para obtener el gestor de conexiones WebSocket (singleton)
def get_ws_manager():
   return ws_manager

def require_role(allowed_roles: list[str]):
    from app.modules.Usuario.schemas import UsuarioPublic

    async def role_checker(
        current_user: Annotated[
            Usuario,
            Depends(get_current_active_user)
        ],
        uow: Annotated[
            UsuarioUnitOfWork,
            Depends(get_usuario_uow)
        ],
    ) -> UsuarioPublic:

        roles = uow.usuario_roles.get_roles_by_user_id(
            current_user.id
        )

        if not any(role in allowed_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permisos insuficientes. "
                    f"Se requiere uno de: {allowed_roles}"
                ),
            )

        return UsuarioPublic(
            id=current_user.id,
            nombre=current_user.nombre,
            apellido=current_user.apellido,
            email=current_user.email,
            celular=current_user.celular,
            activo=current_user.activo,
            roles=roles,
            direcciones=[],
        )

    return role_checker