from sqlmodel import Session, select

from app.Core.repository import BaseRepository
from app.modules.FormaPago.model import FormaPago


class FormaPagoRepository(BaseRepository[FormaPago]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, FormaPago)

    def get_by_codigo(self, codigo: str) -> FormaPago | None:
        return self.session.exec(
            select(FormaPago)
            .where(FormaPago.codigo == codigo)
        ).first()

    def get_all(self) -> list[FormaPago]:
        return list(
            self.session.exec(
                select(FormaPago)
            )
        )