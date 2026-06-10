from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Column, TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import relationship
from app.Core.base import Base


if TYPE_CHECKING:
    from app.modules.Auth.model import RefreshToken
    from app.modules.DireccionEntrega.model import DireccionEntrega
    from app.modules.HistorialPedido.model import HistorialEstadoPedido
    from app.modules.Pedido.model import Pedido
    from app.modules.Rol.model import Rol


#-------------------------------------------
#----------- Tabla Usuario Rol -------------
#-------------------------------------------

# SQLAlchemy ve dos caminos posibles entre usuario y usuario_rol y lanza AmbiguousForeignKeysError porque no sabe cuál usar.
# Al pasar foreign_keys="[UsuarioRol.usuario_id]" le decís explícitamente qué FK usar para cada relación.

class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    usuario_id: int = Field(
        foreign_key="usuario.id",
        primary_key=True
    )

    rol_codigo: str = Field(
        foreign_key="rol.codigo",
        primary_key=True,
        max_length=20
    )

    asignado_por_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id"
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # El atributo asignado_por representa el usuario que asignó un rol, y que para construir esa relación debe usar específicamente la columna asignado_por_id. 
    # El foreign_keys es necesario porque en la tabla probablemente hay más de una FK apuntando a usuario

    asignado_por: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[UsuarioRol.asignado_por_id]", 
        }
    )


#-------------------------------------------
#-------------- Tabla Usuario --------------
#-------------------------------------------

class Usuario(Base, table=True):

    nombre: str = Field(
        min_length=3,
        max_length=80,
        nullable=False
    )

    apellido: str = Field(
        min_length=3,
        max_length=80,
        nullable=False
    )

    email: str = Field(
        max_length=240,
        unique=True,
        nullable=False
    )

    celular: Optional[str] = Field(
        default=None,
        max_length=20,
        nullable=True
    )

    password_hash: str = Field(
        max_length=60,
        nullable=False
    )
    

    # Relationships

    direcciones_entrega: List["DireccionEntrega"] = Relationship(
        back_populates="usuario"
    )

    # Porque un usuario puede iniciar sesión
    # en varios dispositivos varias veces.

    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="usuario"
    )
 

    pedidos: List["Pedido"] = Relationship(
        back_populates="usuario"
    )

    historial_cambios: List["HistorialEstadoPedido"] = Relationship(
        back_populates="usuario"
    )

    usuario_roles: List["UsuarioRol"] = Relationship(
    sa_relationship=relationship(
        "UsuarioRol",
        foreign_keys="[UsuarioRol.usuario_id]",
    )
)