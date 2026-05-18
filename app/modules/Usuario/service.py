from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session

from sqlmodel import Session

from app.Core.config import settings
from app.Core.security import hash_password, verify_password, create_access_token
from app.modules.Rol.model import Rol
from app.modules.Usuario.unit_of_work import UsuarioUnitOfWork
from app.modules.Usuario.model import Usuario
from app.modules.Usuario.schemas import UsuarioCreate, UsuarioList, UsuarioPublic, UsuarioUpdate, Token

class UsuarioService:
    def __init__(self, session: Session) -> None:
        self._session = session
     # ── Helpers privados ───────────────────────────────────────────────────────────
    def _get_or_404(self, uow: UsuarioUnitOfWork, usuario_id: int) -> Usuario:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id {usuario_id} no encontrado",
            )
        return usuario
    def _assert_email_unique(self, uow: UsuarioUnitOfWork, email: str) -> None:
        if uow.usuarios.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email '{email}' ya está en uso",
            )
    
    # ── Casos de uso ──────────────────────────────────────────────────────────────
    def register(self, user_in: UsuarioCreate):
        """Registra un nuevo usuario."""
        with UsuarioUnitOfWork (self._session) as self.uow: 
            if self.uow.usuarios.get_by_email(user_in.email):
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

            # Buscar el rol CLIENT desde la DB
            rol_cliente = self.uow.session.get(Rol, "CLIENT")

            if not rol_cliente:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Rol CLIENT no configurado",
                )

            # Asignar rol al usuario
            usuario.roles.append(rol_cliente)

            # Persistir usuario
            usuario_db = self.uow.usuarios.add(usuario)

        return UsuarioPublic.model_validate(usuario_db)
    

    def authenticate(self, email: str, password: str) -> Token:
        """Autentica con email + password y retorna un JWT."""
        with UsuarioUnitOfWork (self._session) as self.uow: 
            user = self.uow.usuarios.get_by_email(email)

            if not user or not verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            access_token = create_access_token(
                data={
                    "sub": str(user.id),
                    "roles": [rol.codigo for rol in user.roles],
                }
            )

            return Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

    def list_all(self) -> list[Usuario]:
        """Lista todos los usuarios."""
        with UsuarioUnitOfWork (self._session) as self.uow: 
            return self.uow.usuarios.get_all()

    def set_disabled(self, user_id: int, disabled: bool) -> Usuario:
        """Activa o desactiva la cuenta de un usuario."""
        with UsuarioUnitOfWork (self._session) as self.uow: 
            user = self.uow.usuarios.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )
            user.active = False
            user.deleted_at = datetime.now(timezone.utc)
        return self.uow.usuarios.update(user)
