from sqlmodel import Session, select

from app.Core.repository import BaseRepository
from app.modules.DetallePedido.model import DetallePedido


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