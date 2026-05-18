from app.Core.unit_of_work import UnitOfWork
from sqlmodel import Session

from app.Categoria.repository import CategoriaRepository

class CategoriaUnitOfWork(UnitOfWork):
    def __init__(self, session: Session):
        super().__init__(session)
        self.categorias = CategoriaRepository(session)
        #self.productos = ProductoRepository(session)