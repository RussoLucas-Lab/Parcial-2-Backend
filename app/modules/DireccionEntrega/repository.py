from sqlmodel import Session, select

from app.modules.DireccionEntrega.model import DireccionEntrega
from app.Core.repository import BaseRepository


class DireccionEntregaRepository(BaseRepository[DireccionEntrega]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)

    def get_by_id(self, record_id: int) -> DireccionEntrega | None:
        return self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.id == record_id)
            .where(DireccionEntrega.activo == True)
        ).first()

    def get_by_usuario_id(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> list[DireccionEntrega]:
        return list(
            self.session.exec(
                select(DireccionEntrega)
                .where(DireccionEntrega.usuario_id == usuario_id)
                .where(DireccionEntrega.activo == True)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_by_usuario(self, usuario_id: int) -> int:
        return len(
            self.session.exec(
                select(DireccionEntrega)
                .where(DireccionEntrega.usuario_id == usuario_id)
                .where(DireccionEntrega.activo == True)
            ).all()
        )

    def get_active(self, offset: int = 0, limit: int = 20) -> list[DireccionEntrega]:
        return list(
            self.session.exec(
                select(DireccionEntrega)
                .where(DireccionEntrega.activo == True)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def get_principal_by_usuario(self, usuario_id: int):
        statement = select(DireccionEntrega).where(
            DireccionEntrega.usuario_id == usuario_id,
            DireccionEntrega.es_principal == True,
            DireccionEntrega.activo == True
        )

        return self.session.exec(statement).first()

    def count(self) -> int:
        return len(self.session.exec(select(DireccionEntrega)).all())
