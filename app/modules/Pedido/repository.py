from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.Core.repository import BaseRepository
from app.modules.Pedido.model import Pedido


class PedidoRepository(BaseRepository[Pedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)


    def get_by_id(self, record_id: int) -> Pedido | None:
        return self.session.exec(
            select(Pedido)
            .where(Pedido.id == record_id)
            .where(Pedido.activo == True)
        ).first()

    def get_all(self, offset = 0, limit = 20):
        return list(
            self.session.exec(
                select(Pedido)
                .where(Pedido.activo == True)
                .offset(offset)
                .limit(limit)
            )
        )

    def get_by_usuario(self, usuario_id: int, offset: int = 0, limit: int = 20) -> list[Pedido]:
        return list(
            self.session.exec(
                select(Pedido)
                .where(Pedido.usuario_id == usuario_id)
                .where(Pedido.activo == True)
                .offset(offset)
                .limit(limit)
            )
        )


    def get_by_estado(self, estado_codigo: str, offset: int = 0, limit: int = 20) -> list[Pedido]:
        return list(
            self.session.exec(
                select(Pedido)
                .where(Pedido.estado_codigo == estado_codigo)
                .where(Pedido.activo == True)
                .offset(offset)
                .limit(limit)
            )
        )

    def get_by_id_with_relations(self, record_id: int) -> Pedido | None:
        return self.session.exec(
            select(Pedido)
            .options(
                selectinload(Pedido.detalles),
                selectinload(Pedido.historial_estados),
                selectinload(Pedido.usuario),
                selectinload(Pedido.estado),
                selectinload(Pedido.forma_pago),
                selectinload(Pedido.direccion),
            )
            .where(Pedido.id == record_id)
            .where(Pedido.activo == True)
        ).first()

    def count(self) -> int:
        return len(
            self.session.exec(
                select(Pedido)
                .where(Pedido.activo == True)
            ).all()
        )