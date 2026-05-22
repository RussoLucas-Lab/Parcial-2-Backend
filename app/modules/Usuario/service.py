from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, delete, select

from app.Core.config import settings
from app.Core.security import hash_password, verify_password, create_access_token
from app.modules.DireccionEntrega.model import DireccionEntrega
from app.modules.DireccionEntrega.schemas import DireccionEntregaPublic
from app.modules.Rol.model import Rol
from app.modules.Usuario.model import Usuario, UsuarioRol
from app.modules.Usuario.schemas import (
    RolAsignarRequest,
    Token,
    UsuarioCreate,
    UsuarioPublic,
)
from app.modules.Usuario.unit_of_work import UsuarioUnitOfWork


class UsuarioService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_roles(self, usuario_id: int) -> list[str]:
        return list(
            self._session.exec(
                select(UsuarioRol.rol_codigo)
                .where(UsuarioRol.usuario_id == usuario_id)
            ).all()
        )

    def _get_direcciones(self, usuario_id: int) -> list[DireccionEntregaPublic]:
        rows = self._session.exec(
            select(DireccionEntrega).where(DireccionEntrega.usuario_id == usuario_id)
        ).all()
        return [DireccionEntregaPublic.model_validate(d) for d in rows]

    def _to_public(self, user: Usuario) -> UsuarioPublic:
        return UsuarioPublic(
            id=user.id,
            nombre=user.nombre,
            apellido=user.apellido,
            email=user.email,
            celular=user.celular,
            activo=user.activo,
            roles=self._get_roles(user.id),
            direcciones=self._get_direcciones(user.id),
        )

    def _get_or_404(self, uow: UsuarioUnitOfWork, usuario_id: int) -> Usuario:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id {usuario_id} no encontrado",
            )
        return usuario

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def register(self, user_in: UsuarioCreate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_email(user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está registrado",
                )

            usuario = Usuario(
                nombre=user_in.nombre,
                apellido=user_in.apellido,
                email=user_in.email,
                celular=user_in.celular,
                password_hash=hash_password(user_in.password),
            )
            uow.usuarios.add(usuario)  # flush + refresh → populates usuario.id

            rol_client = uow.session.get(Rol, "CLIENT")
            if not rol_client:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Rol CLIENT no configurado en la base de datos",
                )

            uow.session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo="CLIENT"))
            uow.session.flush()

            return UsuarioPublic(
                id=usuario.id,
                nombre=usuario.nombre,
                apellido=usuario.apellido,
                email=usuario.email,
                celular=usuario.celular,
                roles=["CLIENT"],
            )

    def authenticate(self, email: str, password: str) -> Token:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_email(email)
            if not user or not verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            roles = self._get_roles(user.id)
            access_token = create_access_token(
                data={"sub": str(user.id), "roles": roles}
            )

            return Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

    def list_all(self) -> list[UsuarioPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            users = uow.usuarios.get_all()
            return [self._to_public(u) for u in users]

    def set_disabled(self, user_id: int, disabled: bool) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            # session.get busca por PK sin filtrar activo (necesario para reactivar)
            user = uow.session.get(Usuario, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con id {user_id} no encontrado",
                )
            user.activo = not disabled
            user.deleted_at = datetime.now(timezone.utc) if disabled else None
            uow.session.add(user)
            uow.session.flush()
            return self._to_public(user)
    # un solo rol
    def assign_role(
        self, user_id: int, rol_codigo: str, asignado_por_id: int
    ) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)

            rol = uow.session.get(Rol, rol_codigo)
            if not rol:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rol '{rol_codigo}' no existe",
                )

            existing = uow.session.exec(
                select(UsuarioRol)
                .where(UsuarioRol.usuario_id == user_id)
                .where(UsuarioRol.rol_codigo == rol_codigo)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El usuario ya tiene el rol '{rol_codigo}'",
                )

            uow.session.add(
                UsuarioRol(
                    usuario_id=user_id,
                    rol_codigo=rol_codigo,
                    asignado_por_id=asignado_por_id,
                )
            )
            uow.session.flush()
            return self._to_public(user)

    def update_roles(
        self, user_id: int,roles: list[str],updated_by_id: int,
        ) -> UsuarioPublic:

        with UsuarioUnitOfWork(self._session) as uow:

            user = self._get_or_404(uow, user_id)
            current_roles = uow.session.exec(
                select(UsuarioRol).where(
                    UsuarioRol.usuario_id == user_id
                )
            ).all()

            current_role_codes = {
                r.rol_codigo for r in current_roles
            }

            new_role_codes = set(roles)

            roles_to_remove = (
                current_role_codes - new_role_codes
            )

            if roles_to_remove:

                uow.session.exec(
                    delete(UsuarioRol)
                    .where(
                        UsuarioRol.usuario_id == user_id
                    )
                    .where(
                        UsuarioRol.rol_codigo.in_(
                            roles_to_remove
                        )
                    )
                )



            roles_to_add = (
                new_role_codes - current_role_codes
            )

            for rol_codigo in roles_to_add:

                rol = uow.session.get(
                    Rol,
                    rol_codigo,
                )

                if not rol:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Rol '{rol_codigo}' no existe",
                    )

                uow.session.add(
                    UsuarioRol(
                        usuario_id=user_id,
                        rol_codigo=rol_codigo,
                        asignado_por_id=updated_by_id,
                    )
                )

            uow.session.flush()

        return self._to_public(user)


    def revoke_role(self, user_id: int, rol_codigo: str) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            user = self._get_or_404(uow, user_id)

            if rol_codigo == "CLIENT":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede revocar el rol CLIENT",
                )

            usuario_rol = uow.session.exec(
                select(UsuarioRol)
                .where(UsuarioRol.usuario_id == user_id)
                .where(UsuarioRol.rol_codigo == rol_codigo)
            ).first()
            if not usuario_rol:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El usuario no tiene el rol '{rol_codigo}'",
                )

            uow.session.delete(usuario_rol)
            uow.session.flush()
            return self._to_public(user)
