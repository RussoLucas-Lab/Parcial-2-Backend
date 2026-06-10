from unittest import result

from sqlmodel import Session, func, select

from app.Core.repository import BaseRepository
from app.modules.DetallePedido.model import DetallePedido
from app.modules.Producto.model import Producto


class DetallePedidoRepository(BaseRepository[DetallePedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, DetallePedido)

    def get_by_id(self, pedido_id: int, producto_id: int) -> DetallePedido | None:
        return self.session.exec(
            select(DetallePedido)
            .where(DetallePedido.pedido_id == pedido_id)
            .where(DetallePedido.producto_id == producto_id)
        ).first()

    def get_by_pedido(self, pedido_id: int) -> list[DetallePedido]:
        return list(
            self.session.exec(
                select(DetallePedido)
                .where(DetallePedido.pedido_id == pedido_id)
            )
        )

    def count_by_pedido(self, pedido_id: int) -> int:
        return len(
            self.session.exec(
                select(DetallePedido)
                .where(DetallePedido.pedido_id == pedido_id)
            ).all()
        )
    
    def get_top_productos(
    self,
    limit: int = 10
    ) -> list[dict[str, any]]:

        statement = (
            select(
                Producto.nombre.label("producto"),
                func.sum(
                    DetallePedido.cantidad
                ).label("cantidad")
            )
            .join(
                DetallePedido,
                Producto.id == DetallePedido.producto_id
            )
            .where(
                Producto.deleted_at.is_(None)
            )
            .where(
                DetallePedido.deleted_at.is_(None)
            )
            .group_by(
                Producto.id,
                Producto.nombre
            )
            .order_by(
                func.sum(
                    DetallePedido.cantidad
                ).desc()
            )
            .limit(limit)
        )

        result = self.session.exec(statement).all()

        return [
            {
                "producto": row.producto,
                "cantidad": row.cantidad
            }
            for row in result
        ]