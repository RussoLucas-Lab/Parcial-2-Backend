from app.Core.unit_of_work import UnitOfWork
from sqlmodel import Session

from app.modules.Ingrediente.repository import IngredienteRepository
from app.modules.Producto.repository import ProductoRepository


class IngredienteUnitOfWork(UnitOfWork):
    def __init__(self, session: Session):
        super().__init__(session)
        self.ingredientes = IngredienteRepository(session)
       