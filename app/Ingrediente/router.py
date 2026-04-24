from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.Core.database import get_session
from app.Ingrediente.schemas import (
    IngredienteCreate,
    IngredienteList,
    IngredientePublic,
    IngredienteUpdate,
)
from app.Ingrediente.service import IngredienteService


router = APIRouter(prefix="/ingredientes", tags=["Ingredientes"])


def get_ingrediente_service(
    session: Session = Depends(get_session),
) -> IngredienteService:
    return IngredienteService(session)


@router.post(
    "/",
    response_model=IngredientePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un ingrediente",
)
def create_ingrediente(
    data: IngredienteCreate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=IngredienteList,
    summary="Listar ingredientes (paginado)",
)
def list_ingredientes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{ingrediente_id}",
    response_model=IngredientePublic,
    summary="Obtener ingrediente por ID",
)
def get_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.get_by_id(ingrediente_id)


@router.patch(
    "/{ingrediente_id}",
    response_model=IngredientePublic,
    summary="Actualización parcial de ingrediente",
)
def update_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.update(ingrediente_id, data)


@router.delete(
    "/{ingrediente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete de ingrediente",
)
def delete_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> None:
    svc.soft_delete(ingrediente_id)