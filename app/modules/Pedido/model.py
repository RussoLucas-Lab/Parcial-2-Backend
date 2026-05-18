from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Numeric,
    String,
    Text
)

from sqlmodel import Field, Relationship

from app.Core.base import Base


if TYPE_CHECKING:
    from app.modules.DetallePedido.model import DetallePedido
    from app.modules.DireccionEntrega.model import DireccionEntrega
    from app.modules.EstadoPedido.model import EstadoPedido
    from app.modules.FormaPago.model import FormaPago
    from app.modules.HistorialPedido.model import HistorialEstadoPedido
    from app.modules.Usuario.model import Usuario


#-------------------------------------------
#-------------- Tabla Pedido ---------------
#-------------------------------------------

class Pedido(Base, table=True):
    __tablename__ = "pedido"

    __table_args__ = (
        CheckConstraint(
            "total >= 0",
            name="ck_pedido_total_positive"
        ),
    )

    id: int = Field(
        sa_column=Column(
            BigInteger,
            primary_key=True,
            autoincrement=True
        )
    )

    usuario_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("usuario.id"),
            nullable=False
        )
    )

    direccion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("direccion_entrega.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    estado_codigo: str = Field(
        sa_column=Column(
            String(20),
            ForeignKey("estado_pedido.codigo"),
            nullable=False
        )
    )

    forma_pago_codigo: str = Field(
        sa_column=Column(
            String(20),
            ForeignKey("forma_pago.codigo"),
            nullable=False
        )
    )

    subtotal: Decimal = Field(
        sa_column=Column(
            Numeric(10, 2),
            nullable=False
        )
    )

    descuento: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(
            Numeric(10, 2),
            nullable=False,
            default=0.00
        )
    )

    costo_envio: Decimal = Field(
        default=Decimal("50.00"),
        sa_column=Column(
            Numeric(10, 2),
            nullable=False,
            default=50.00
        )
    )

    total: Decimal = Field(
        sa_column=Column(
            Numeric(10, 2),
            nullable=False
        )
    )

    notas: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    # Relationships

    usuario: "Usuario" = Relationship(
        back_populates="pedidos"
    )

    direccion: Optional["DireccionEntrega"] = Relationship(
        back_populates="pedidos"
    )

    estado: "EstadoPedido" = Relationship(
        back_populates="pedidos"
    )

    forma_pago: "FormaPago" = Relationship(
        back_populates="pedidos"
    )

    historial_estados: List["HistorialEstadoPedido"] = Relationship(
        back_populates="pedido"
    )

    detalles: List["DetallePedido"] = Relationship(
        back_populates="pedido"
    )