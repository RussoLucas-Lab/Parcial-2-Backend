from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.Producto.schemas import (
    ProductoCreate,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.Producto.unit_of_work import ProductoUnitOfWork
from app.Producto.model import Producto


class ProductoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        producto = uow.productos.get_by_id(producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id {producto_id} no encontrado",
            )
        return producto

    def _get_ingredientes(self, uow: ProductoUnitOfWork, ids: list[int]):
        if not ids:
            return []
        ingredientes = uow.ingredientes.get_by_ids(ids)

        if len(ingredientes) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno o más ingredientes no existen",
            )
        return ingredientes

    def _get_categorias(self, uow: ProductoUnitOfWork, ids: list[int]):
        if not ids:
            return []
        categorias = uow.categorias.get_by_ids(ids)

        if len(categorias) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Una o más categorias no existen",
            )
        return categorias

    # ── Casos de uso ───────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:

            ingredientes = self._get_ingredientes(uow, data.ingrediente_ids)
            categorias = self._get_categorias(uow, data.categoria_ids)

            producto = Producto.model_validate(
                data.model_dump(exclude={"ingrediente_ids", "categoria_ids"})
            )

            # 🔥 asignar relaciones
            producto.ingredientes = ingredientes
            producto.categorias = categorias

            uow.productos.add(producto)

            return ProductoPublic.model_validate(producto, from_attributes=True)

    def get_all(self, offset: int = 0, limit: int = 20) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_active_with_relations(offset=offset, limit=limit)
            total = uow.productos.count()

            return ProductoList(
                data=[
                    ProductoPublic.model_validate(p, from_attributes=True)
                    for p in productos
                ],
                total=total
            )
            

    def get_by_id(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            return ProductoPublic.model_validate(
                producto,
                from_attributes=True
            )

    def update(self, producto_id: int, data: ProductoUpdate):
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            patch = data.model_dump(exclude_unset=True)

            if "ingrediente_ids" in patch:
                producto.ingredientes = self._get_ingredientes(
                    uow, patch.pop("ingrediente_ids")
                )

            if "categoria_ids" in patch:
                producto.categorias = self._get_categorias(
                    uow, patch.pop("categoria_ids")
                )

            for field, value in patch.items():
                setattr(producto, field, value)

            producto.updated_at = datetime.now(timezone.utc)

            uow.productos.add(producto)

            #return producto
            return ProductoPublic.model_validate(producto, from_attributes=True) 

    def soft_delete(self, producto_id: int) -> None:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            producto.activo = False
            uow.productos.add(producto)