from sqlmodel import Session, select

from app.Core.repository import BaseRepository

from app.modules.Usuario.model import UsuarioRol


class UsuarioRolRepository(BaseRepository[UsuarioRol]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, UsuarioRol)

    def get_by_user_and_role(
        self,
        user_id: int,
        rol_codigo: str,
    ) -> UsuarioRol | None:

        statement = (
            select(UsuarioRol)
            .where(UsuarioRol.usuario_id == user_id)
            .where(UsuarioRol.rol_codigo == rol_codigo)
        )

        return self.session.exec(statement).first()

    def get_roles_by_user_id(
        self,
        user_id: int,
    ) -> list[str]:

        statement = (
            select(UsuarioRol.rol_codigo)
            .where(UsuarioRol.usuario_id == user_id)
        )

        return list(
            self.session.exec(statement).all()
        )

    def get_user_roles(
        self,
        user_id: int,
    ) -> list[UsuarioRol]:

        statement = (
            select(UsuarioRol)
            .where(UsuarioRol.usuario_id == user_id)
        )

        return list(
            self.session.exec(statement).all()
        )

    def exists(
        self,
        user_id: int,
        rol_codigo: str,
    ) -> bool:

        return (
            self.get_by_user_and_role(
                user_id,
                rol_codigo,
            )
            is not None
        )

    def delete_by_user_and_role(
        self,
        user_id: int,
        rol_codigo: str,
    ) -> bool:

        usuario_rol = self.get_by_user_and_role(
            user_id,
            rol_codigo,
        )

        if not usuario_rol:
            return False

        self.session.delete(usuario_rol)

        return True