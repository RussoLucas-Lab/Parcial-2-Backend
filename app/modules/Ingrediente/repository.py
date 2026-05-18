from sqlmodel import Session, select

from app.Core.repository import BaseRepository
from app.modules.Ingrediente.model import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):

    # Inicializar el repositorio de Ingrediente

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)
    
    def get_by_id(self, record_id: int) -> Ingrediente | None:
        return self.session.exec(
            select(Ingrediente)
            .where(Ingrediente.id == record_id)
            .where(Ingrediente.activo == True)
        ).first()

    def get_by_ids(self, ids: list[int]):
        if not ids:
            return []

        statement = select(self.model).where(self.model.id.in_(ids))
        return self.session.exec(statement).all()

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:    
        return self.session.exec(
            select(Ingrediente)
            .where(Ingrediente.nombre == nombre)
            .where(Ingrediente.activo == True)
        ).first()


    def get_all(self, offset = 0, limit = 20):
        return super().get_all(offset, limit)

    def get_active(self, offset: int = 0, limit: int = 20) -> list[Ingrediente]:
        return list(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.activo == True)
            )
        )
    def count(self) -> int:

        return len(self.session.exec(select(Ingrediente)).all())
        