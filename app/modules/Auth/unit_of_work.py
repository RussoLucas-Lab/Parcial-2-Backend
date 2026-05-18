from sqlmodel import Session

from app.Core.unit_of_work import UnitOfWork
from app.modules.Auth.repository import RefreshTokenRepository
from app.modules.Usuario.repository import UsuarioRepository


class AuthUnitOfWork(UnitOfWork):
    def __init__(self, session: Session):
        super().__init__(session)
        self.tokens = RefreshTokenRepository(session)
        self.usuarios = UsuarioRepository(session)
