from sqlmodel import Session, select

from app.Core.repository import BaseRepository
from app.modules.HistorialPedido.model import HistorialEstadoPedido


class HistorialEstadoPedidoRepository(BaseRepository[HistorialEstadoPedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, HistorialEstadoPedido)


    def get_by_id(self, record_id: int) -> HistorialEstadoPedido | None:
        return self.session.exec(
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.id == record_id)
        ).first()


    def get_by_pedido(self, pedido_id: int) -> list[HistorialEstadoPedido]:
        return list(
            self.session.exec(
                select(HistorialEstadoPedido)
                .where(HistorialEstadoPedido.pedido_id == pedido_id)
            )
        )


    def get_last_by_pedido(self, pedido_id: int) -> HistorialEstadoPedido | None:
        return self.session.exec(
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.id.desc())
        ).first()

    def count_by_pedido(self, pedido_id: int) -> int:
        return len(
            self.session.exec(
                select(HistorialEstadoPedido)
                .where(HistorialEstadoPedido.pedido_id == pedido_id)
            ).all()
        )