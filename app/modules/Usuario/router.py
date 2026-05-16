from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.deps import get_current_active_user, require_role
from app.modules.Usuario.model import Usuario
from app.modules.Usuario.schemas import (
    RolAsignarRequest,
    UsuarioCreate,
    UsuarioPublic,
)
from app.modules.Usuario.service import UsuarioService

router = APIRouter(prefix="/api/v1", tags=["usuarios"])


def get_usuario_service(
    session: Session = Depends(get_session),
) -> UsuarioService:
    return UsuarioService(session)


# ── Registro ──────────────────────────────────────────────────────────────────

@router.post(
    "/auth/register",
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario (asigna rol CLIENT automáticamente)",
)
def register(
    user_in: UsuarioCreate,
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc.register(user_in)


# ── Perfil del usuario autenticado ────────────────────────────────────────────

@router.get(
    "/auth/me",
    response_model=UsuarioPublic,
    summary="Obtener perfil del usuario autenticado (incluye roles)",
)
def read_me(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc._to_public(current_user)


# ── Administración de usuarios (ADMIN) ────────────────────────────────────────

@router.get(
    "/usuarios",
    response_model=list[UsuarioPublic],
    summary="Listar todos los usuarios",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
def list_users(svc: UsuarioService = Depends(get_usuario_service)):
    return svc.list_all()


@router.post(
    "/usuarios/{user_id}/desactivar",
    response_model=UsuarioPublic,
    summary="Desactivar cuenta de usuario (soft delete)",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
def deactivate_user(
    user_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc.set_disabled(user_id=user_id, disabled=True)


@router.post(
    "/usuarios/{user_id}/activar",
    response_model=UsuarioPublic,
    summary="Reactivar cuenta de usuario",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
def activate_user(
    user_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc.set_disabled(user_id=user_id, disabled=False)


# ── Gestión de roles (ADMIN) ──────────────────────────────────────────────────

@router.post(
    "/usuarios/{user_id}/roles",
    response_model=UsuarioPublic,
    status_code=status.HTTP_200_OK,
    summary="Asignar un rol a un usuario",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
def assign_role(
    user_id: int,
    data: RolAsignarRequest,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc.assign_role(
        user_id=user_id,
        rol_codigo=data.rol_codigo,
        asignado_por_id=current_user.id,
    )


@router.delete(
    "/usuarios/{user_id}/roles/{rol_codigo}",
    response_model=UsuarioPublic,
    status_code=status.HTTP_200_OK,
    summary="Revocar un rol de un usuario",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
def revoke_role(
    user_id: int,
    rol_codigo: str,
    svc: UsuarioService = Depends(get_usuario_service),
):
    return svc.revoke_role(user_id=user_id, rol_codigo=rol_codigo)
