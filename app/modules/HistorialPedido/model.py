from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String
)

from sqlmodel import Field, Relationship

from app.Core.base import Base


if TYPE_CHECKING:
    from app.modules.EstadoPedido.model import EstadoPedido
    from app.modules.Pedido.model import Pedido
    from app.modules.Usuario.model import Usuario


#-------------------------------------------
#----- Tabla Historial Estado Pedido -------
#-------------------------------------------

class HistorialEstadoPedido(Base, table=True):
    __tablename__ = "historial_estado_pedido"

    id: int = Field(
        sa_column=Column(
            BigInteger().with_variant(Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True
        )
    )

    pedido_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("pedido.id"),
            nullable=False
        )
    )

    estado_desde: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String(20),
            ForeignKey("estado_pedido.codigo"),
            nullable=True
        )
    )

    estado_hacia: str = Field(
        sa_column=Column(
            String(20),
            ForeignKey("estado_pedido.codigo"),
            nullable=False
        )
    )

    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("usuario.id"),
            nullable=True
        )
    )

    # Relationships

    pedido: "Pedido" = Relationship(
        back_populates="historial_estados"
    )

    usuario: "Usuario" = Relationship(
        back_populates="historial_cambios"
    )

    estado_desde_rel: Optional["EstadoPedido"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_desde]"
        },
        back_populates="historial_desde"
    )

    estado_hacia_rel: "EstadoPedido" = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_hacia]"
        },
        back_populates="historial_hacia"
    )