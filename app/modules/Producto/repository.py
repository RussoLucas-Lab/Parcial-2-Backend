from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.Core.repository import BaseRepository
from app.modules.Producto.model import Producto

class ProductoRepository(BaseRepository[Producto]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)
    
    def get_by_id(self, record_id: int) -> Producto | None:
        return self.session.exec(
            select(Producto)
            .where(Producto.id == record_id)
            .where(Producto.activo == True)
        ).first()

    def get_by_nombre(self, nombre: str) -> Producto | None:    
        return self.session.exec(
            select(Producto).where(Producto.nombre == nombre)
        ).first()


    def get_all(self, offset = 0, limit = 20):
        return super().get_all(offset, limit)

    def get_active(self, offset: int = 0, limit: int = 20) -> list[Producto]:
        return list(
            self.session.exec(
                select(Producto)
                .where(Producto.activo == True)
            )
        )

    def get_active_with_relations(self, offset=0, limit=20):
        statement = (
            select(Producto)
            .options(
                selectinload(Producto.categorias),
                selectinload(Producto.ingredientes) #hace 3 queries optimizadas (productos + relaciones)
            )
            .where(Producto.activo == True)
            .offset(offset)
            .limit(limit)
    )

        return list(self.session.exec(statement))

    def count(self) -> int:

        return len(self.session.exec(select(Producto).where(Producto.activo == True)).all())