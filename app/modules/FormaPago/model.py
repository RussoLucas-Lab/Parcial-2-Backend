from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel


if TYPE_CHECKING:
    from app.modules.Pedido.model import Pedido


#-------------------------------------------
#----------- Tabla Forma Pago --------------
#-------------------------------------------

class FormaPago(SQLModel, table=True):
    __tablename__ = "forma_pago"

    codigo: str = Field(
        primary_key=True,
        max_length=20
    )

    descripcion: Optional[str] = Field(
        default=None
    )

    # Relationships

    pedidos: List["Pedido"] = Relationship(
        back_populates="forma_pago"
    )