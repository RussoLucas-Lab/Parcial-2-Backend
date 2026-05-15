from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Column, Integer, String

from sqlmodel import Field, Relationship, SQLModel




if TYPE_CHECKING:
    from app.modules.Pedido.model import Pedido
    from app.modules.HistorialPedido.model import HistorialEstadoPedido


#-------------------------------------------
#--------- Tabla Estado Pedido -------------
#-------------------------------------------

class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estado_pedido"

    codigo: str = Field(
        sa_column=Column(
            String(20),
            primary_key=True
        )
    )

    descripcion: str = Field(
        sa_column=Column(
            String(80),
            nullable=False
        )
    )

    orden: int = Field(
        sa_column=Column(
            Integer,
            nullable=False
        )
    )

    es_terminal: bool = Field(
        sa_column=Column(
            Boolean,
            nullable=False
        )
    )

    # Relationships

    pedidos: List["Pedido"] = Relationship(
        back_populates="estado"
    )

    historial_desde: List["HistorialEstadoPedido"] = Relationship(
    sa_relationship_kwargs={
        "foreign_keys": "[HistorialEstadoPedido.estado_desde]"
    },
    back_populates="estado_desde_rel"
    )

    historial_hacia: List["HistorialEstadoPedido"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_hacia]"
        },
        back_populates="estado_hacia_rel"
    )