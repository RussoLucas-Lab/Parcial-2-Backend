from decimal import Decimal
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.DetallePedido.model import DetallePedido
from app.modules.DetallePedido.schemas import (
    DetallePedidoCreate,
    DetallePedidoResponse
)
from app.modules.DetallePedido.unit_of_work import DetallePedidoUnitOfWork


class DetallePedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_producto_or_404(self, uow, producto_id: int):
        producto = uow.productos.get_by_id(producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {producto_id} no encontrado"
            )
        return producto

    def _get_pedido_or_404(self, uow, pedido_id: int):
        pedido = uow.pedidos.get_by_id(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido {pedido_id} no encontrado"
            )
        return pedido

    # ── Casos de uso ───────────────────────────────────────────────────────────

    def create(
        self,
        pedido_id: int,
        data: DetallePedidoCreate
    ) -> DetallePedidoResponse:

        with DetallePedidoUnitOfWork(self._session) as uow:

            pedido = self._get_pedido_or_404(uow, pedido_id)
            producto = self._get_producto_or_404(uow, data.producto_id)

            precio = Decimal(producto.precio)
            cantidad = data.cantidad

            subtotal = precio * cantidad

            detalle = DetallePedido(
                pedido_id=pedido.id,
                producto_id=producto.id,
                cantidad=cantidad,
                nombre_snapshot=producto.nombre,
                precio_snapshot=precio,
                subtotal_snap=subtotal,
                personalizacion=data.personalizacion
            )

            uow.detalles.add(detalle)

            return DetallePedidoResponse.model_validate(
                detalle,
                from_attributes=True
            )


    def get_by_pedido(self, pedido_id: int) -> list[DetallePedidoResponse]:

        with DetallePedidoUnitOfWork(self._session) as uow:

            detalles = uow.detalles.get_by_pedido(pedido_id)

            return [
                DetallePedidoResponse.model_validate(d, from_attributes=True)
                for d in detalles
            ]