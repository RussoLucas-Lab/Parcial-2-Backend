from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.permission import require_same_user_or_admin
from app.modules.DireccionEntrega.schemas import (
    DireccionEntregaCreate,
    DireccionEntregaList,
    DireccionEntregaPublic,
    DireccionEntregaUpdate,
)
from app.modules.DireccionEntrega.service import DireccionEntregaService


router = APIRouter(
    prefix="/api/v1/usuarios/{usuario_id}/direcciones",
    tags=["DireccionesEntrega"],
    dependencies=[
        Depends(require_same_user_or_admin)
    ],
)


def get_direccion_service(
    session: Session = Depends(get_session),
) -> DireccionEntregaService:
    return DireccionEntregaService(session)


# ── Crear ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=DireccionEntregaPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una dirección de entrega para un usuario",
)
def create_direccion(
    usuario_id: int,
    data: DireccionEntregaCreate,
    svc: DireccionEntregaService = Depends(get_direccion_service),
) -> DireccionEntregaPublic:
    return svc.create(usuario_id, data)


# ── Listar ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=DireccionEntregaList,
    status_code=status.HTTP_200_OK,
    summary="Listar direcciones de entrega de un usuario (paginado)",
)
def list_direcciones(
    usuario_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: DireccionEntregaService = Depends(get_direccion_service),
) -> DireccionEntregaList:
    return svc.list_by_usuario(usuario_id, offset=offset, limit=limit)


# ── Obtener por ID ────────────────────────────────────────────────────────────

@router.get(
    "/{direccion_id}",
    response_model=DireccionEntregaPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener una dirección de entrega por ID",
)
def get_direccion(
    usuario_id: int,
    direccion_id: int,
    svc: DireccionEntregaService = Depends(get_direccion_service),
) -> DireccionEntregaPublic:
    return svc.get_by_id(usuario_id, direccion_id)


# ── Actualizar ────────────────────────────────────────────────────────────────

@router.patch(
    "/{direccion_id}",
    response_model=DireccionEntregaPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualización parcial de una dirección de entrega",

)
def update_direccion(
    usuario_id: int,
    direccion_id: int,
    data: DireccionEntregaUpdate,
    svc: DireccionEntregaService = Depends(get_direccion_service),
) -> DireccionEntregaPublic:
    return svc.update(usuario_id, direccion_id, data)


# ── Soft delete ───────────────────────────────────────────────────────────────

@router.delete(
    "/{direccion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete de una dirección de entrega",
)
def delete_direccion(
    usuario_id: int,
    direccion_id: int,
    svc: DireccionEntregaService = Depends(get_direccion_service),
) -> None:
    svc.soft_delete(usuario_id, direccion_id)
