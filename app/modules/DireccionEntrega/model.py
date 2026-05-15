from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Numeric

from sqlmodel import Field, Relationship

from app.Core.base import Base


if TYPE_CHECKING:
    from app.modules.Pedido.model import Pedido
    from app.modules.Usuario.model import Usuario


#-------------------------------------------
#------ Tabla Direccion Entrega ------------
#-------------------------------------------

class DireccionEntrega(Base, table=True):
    __tablename__ = "direccion_entrega"

    usuario_id: int = Field(
        foreign_key="usuario.id",
        nullable=False
    )

    alias: Optional[str] = Field(
        default=None,
        max_length=50
    )

    linea1: str = Field(
        nullable=False
    )

    linea2: Optional[str] = Field(
        default=None
    )

    ciudad: str = Field(
        max_length=100,
        nullable=False
    )

    provincia: Optional[str] = Field(
        default=None,
        max_length=100
    )

    codigo_postal: Optional[str] = Field(
        default=None,
        max_length=10
    )

    latitud: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(
            Numeric(9, 6)
        )
    )

    longitud: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(
            Numeric(9, 6)
        )
    )

    es_principal: bool = Field(
        default=False,
        nullable=False
    )

    # Relationships

    usuario: "Usuario" = Relationship(
        back_populates="direcciones_entrega"
    )

    pedidos: List["Pedido"] = Relationship(
        back_populates="direccion"
    )