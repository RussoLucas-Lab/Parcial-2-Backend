from sqlmodel import Session

from app.Core.database import engine
from app.Core.unit_of_work import UnitOfWork


from app.modules.Usuario.UsuarioRol_repository import UsuarioRolRepository
from app.modules.Usuario.repository import UsuarioRepository


class UsuarioUnitOfWork(UnitOfWork):

    def __init__(self, session: Session):
        super().__init__(session)

        self.usuarios = UsuarioRepository(session)
        self.usuario_roles = UsuarioRolRepository(session)
        

def get_usuario_uow():

    with Session(engine) as session:
        yield UsuarioUnitOfWork(session)