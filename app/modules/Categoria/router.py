from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.deps import require_role
from app.modules.Categoria.schemas import (
    CategoriaCreate,
    CategoriaList,
    CategoriaPublic,
    CategoriaTree,
    CategoriaUpdate,
)
from app.modules.Categoria.service import CategoriaService


router = APIRouter(prefix="/api/v1/categorias", tags=["Categorias"],)


def get_categoria_service(
    session: Session = Depends(get_session),
) -> CategoriaService:
    return CategoriaService(session)


@router.post(
    "/",
    response_model=CategoriaPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una categoria",
    dependencies=[
        Depends(require_role(["ADMIN"]))
    ],
)
def create_categoria(
    data: CategoriaCreate,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=CategoriaList,
    status_code=status.HTTP_200_OK,
    summary="Listar categorias (paginado)",
)
def list_categorias(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{categoria_id}",
    response_model=CategoriaPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener categoria por ID",
)
def get_categoria(
    categoria_id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.get_by_id(categoria_id)


@router.patch(
    "/{categoria_id}",
    response_model=CategoriaPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualización parcial de categoria",
    dependencies=[
        Depends(require_role(["ADMIN"]))
    ],
)
def update_categoria(
    categoria_id: int,
    data: CategoriaUpdate,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.update(categoria_id, data)


@router.delete(
    "/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete de categoria",
    dependencies=[
        Depends(require_role(["ADMIN"]))
    ],
)
def delete_categoria(
    categoria_id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> None:
    svc.soft_delete(categoria_id)

@router.get("/categorias/tree", response_model=list[CategoriaTree])
def get_categorias_tree(svc: CategoriaService = Depends(get_categoria_service)):
    return svc.get_all_tree()