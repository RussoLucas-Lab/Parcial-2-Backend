from app.Core.unit_of_work import UnitOfWork
from sqlmodel import Session

from app.modules.Categoria.repository import CategoriaRepository
from app.modules.Producto.repository import ProductoRepository

class CategoriaUnitOfWork(UnitOfWork):
    def __init__(self, session: Session):
        super().__init__(session)
        self.categorias = CategoriaRepository(session)
        self.productos = ProductoRepository(session)
        
    def __enter__(self) -> "CategoriaUnitOfWork":
        return self
        
        