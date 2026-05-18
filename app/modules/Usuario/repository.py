from sqlmodel import Session, select

from app.modules.Usuario.model import Usuario
from app.Core.repository import BaseRepository

class UsuarioRepository(BaseRepository[Usuario]):
   def __init__(self, session: Session) -> None:
      super().__init__(session, Usuario)

   def get_by_id(self, record_id: int) -> Usuario | None:
        return self.session.exec(
            select(Usuario)
            .where(Usuario.id == record_id)
            .where(Usuario.activo == True)
        ).first()

   def get_by_ids(self, ids: list[int]):
      if not ids:
         return []

      statement = select(self.model).where(self.model.id.in_(ids))
      return self.session.exec(statement).all()

   def get_by_email(self, email: str) -> Usuario | None:    
      return self.session.exec(
         select(Usuario).where(Usuario.email == email)
         .where(Usuario.activo == True)   
      ).first()

   def get_all(self, offset = 0, limit = 20):
      return super().get_all(offset, limit)

   def get_active(self, offset: int = 0, limit: int = 20) -> list[Usuario]:
      return list(
         self.session.exec(
               select(Usuario)
               .where(Usuario.activo == True)
         )
      )
   
   def count(self) -> int:
      return len(self.session.exec(select(Usuario)).all())


    
