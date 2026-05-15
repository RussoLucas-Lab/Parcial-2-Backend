
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.modules.Usuario.schemas import (
    UsuarioCreate,
    UsuarioPublic,
    Token,
)

from app.modules.Usuario.model import Usuario
from app.modules.Usuario.service import UsuarioService
from app.modules.Usuario.unit_of_work import (
    UsuarioUnitOfWork,
    get_usuario_uow,
)

from app.Core.deps import get_current_active_user


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


# ── Registro ───────────────────────────────────────────────────────────



@router.post(
    "/register",
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UsuarioCreate,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.register(user_in)


# ── Login ─────────────────────────────────────────────────────────────

@router.post(
    "/token",
    response_model=Token,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)

        token = service.authenticate(
            email=form_data.username,
            password=form_data.password,
        )

        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            secure=False,  # True en producción HTTPS
            samesite="lax",
            max_age=token.expires_in,
        )

        return token


# ── Logout ─────────────────────────────────────────────────────────────

@router.post("/logout")
def logout(response: Response):

    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return {
        "message": "Sesión cerrada correctamente"
    }


# ─── Usuario autenticado ──────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UsuarioPublic,
)
def read_me(
    current_user: Annotated[
        Usuario,
        Depends(get_current_active_user)
    ],
):
    return current_user


# ── Ruta protegida ───────────────────────────────────────────────────────────


@router.get("/privado")
def ruta_privada(
    current_user: Annotated[
        Usuario,
        Depends(get_current_active_user)
    ],
):
    return {
        "mensaje": (
            f"Hola {current_user.nombre} "
            f"{current_user.apellido}"
        ),
        "email": current_user.email,
    }


# ── Listar ───────────────────────────────────────────────────────────

@router.get(
    "/usuarios",
    response_model=list[UsuarioPublic],
)
def list_users(
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.list_all()


# ── Desactivar ───────────────────────────────────────────────────────────

@router.post(
    "/usuarios/{user_id}/desactivar",
    response_model=UsuarioPublic,
)
def deactivate_user(
    user_id: int,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(
            user_id=user_id,
            disabled=True,
        )


# ── Activar ─────────────────────────────────────────────────────────

@router.post(
    "/usuarios/{user_id}/activar",
    response_model=UsuarioPublic,
)
def activate_user(
    user_id: int,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_usuario_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(
            user_id=user_id,
            disabled=False,
        )