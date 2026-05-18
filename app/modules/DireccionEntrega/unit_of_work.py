from sqlmodel import Session

from app.Core.unit_of_work import UnitOfWork
from app.modules.DireccionEntrega.repository import DireccionEntregaRepository
from app.modules.Usuario.repository import UsuarioRepository


class DireccionEntregaUnitOfWork(UnitOfWork):
    def __init__(self, session: Session):
        super().__init__(session)
        self.direcciones = DireccionEntregaRepository(session)
        self.usuarios = UsuarioRepository(session)
