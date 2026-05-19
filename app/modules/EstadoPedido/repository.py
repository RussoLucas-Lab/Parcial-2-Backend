from sqlmodel import Session, select

from app.Core.repository import BaseRepository
from app.modules.EstadoPedido.model import EstadoPedido


class EstadoPedidoRepository(BaseRepository[EstadoPedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, EstadoPedido)


    def get_by_codigo(self, codigo: str) -> EstadoPedido | None:
        return self.session.exec(
            select(EstadoPedido)
            .where(EstadoPedido.codigo == codigo)
        ).first()


    def get_all_ordered(self) -> list[EstadoPedido]:
        return list(
            self.session.exec(
                select(EstadoPedido)
                .order_by(EstadoPedido.orden)
            )
        )


    def get_terminal_states(self) -> list[EstadoPedido]:
        return list(
            self.session.exec(
                select(EstadoPedido)
                .where(EstadoPedido.es_terminal == True)
            )
        )