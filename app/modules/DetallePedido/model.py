from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Numeric,
    SmallInteger,
    String
)

from sqlalchemy.dialects.postgresql import ARRAY

from sqlmodel import Field, Relationship, SQLModel

from app.Core.base import Base
from app.modules.Pedido.model import Pedido

if TYPE_CHECKING:
    
    from app.modules.Producto.model import Producto


#-------------------------------------------
#--------- Tabla Detalle Pedido ------------
#-------------------------------------------

class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalle_pedido"

    __table_args__ = (
        CheckConstraint(
            "cantidad >= 1",
            name="ck_detalle_pedido_cantidad_positive"
        ),
        CheckConstraint(
            "precio_snapshot >= 0",
            name="ck_detalle_pedido_precio_positive"
        ),
    )

    # PK compuesta

    pedido_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("pedido.id", ondelete="CASCADE"),
            primary_key=True
        )
    )

    producto_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("producto.id", ondelete="RESTRICT"),
            primary_key=True
        )
    )

    # Atributos

    cantidad: int = Field(
        sa_column=Column(
            SmallInteger,
            nullable=False
        )
    )

    nombre_snapshot: str = Field(
        sa_column=Column(
            String(200),
            nullable=False
        )
    )

    precio_snapshot: Decimal = Field(
        sa_column=Column(
            Numeric(10, 2),
            nullable=False
        )
    )

    subtotal_snap: Decimal = Field(
        sa_column=Column(
            Numeric(10, 2),
            nullable=False
        )
    )

    personalizacion: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(
            ARRAY(BigInteger),
            nullable=True
        )
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    deleted_at: Optional[datetime] = Field(
        default=None,
        nullable=True
    )

    # Relationships

    pedido: "Pedido" = Relationship(
        back_populates="detalles"
    )

    producto: "Producto" = Relationship(
        back_populates="detalles_pedido"
    )