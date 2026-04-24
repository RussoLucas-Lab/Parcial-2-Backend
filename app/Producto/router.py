from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.Core.database import get_session
from app.Producto.schemas import (
    ProductoCreate,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.Producto.service import ProductoService


router = APIRouter(prefix="/productos", tags=["Productos"])


def get_producto_service(
    session: Session = Depends(get_session),
) -> ProductoService:
    return ProductoService(session)


@router.post(
    "/",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un producto",
)
def create_producto(
    data: ProductoCreate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=ProductoList,
    status_code=status.HTTP_200_OK,
    summary="Listar productos (paginado)",
)
def list_productos(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{producto_id}",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener producto por ID",
)
def get_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.get_by_id(producto_id)


@router.patch(
    "/{producto_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductoPublic,
    summary="Actualización parcial de producto",
)
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.update(producto_id, data)


@router.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete de producto",
)
def delete_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> None:
    svc.soft_delete(producto_id)