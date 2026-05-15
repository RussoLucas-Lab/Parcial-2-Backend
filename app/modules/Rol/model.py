from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.modules.Usuario.model import UsuarioRol


if TYPE_CHECKING:
    from app.modules.Usuario.model import Usuario


#-------------------------------------------
#--------------- Tabla Rol -----------------
#-------------------------------------------

class Rol(SQLModel, table=True):
    __tablename__ = "rol"

    codigo: str = Field(
        primary_key=True,
        max_length=20
    )

    nombre: str = Field(
        unique=True,
        nullable=False,
        max_length=50
    )

    descripcion: Optional[str] = Field(
        default=None
    )


    
