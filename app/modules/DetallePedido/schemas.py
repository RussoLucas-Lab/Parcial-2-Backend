from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class DetallePedidoCreate(BaseModel):

    producto_id: int
    cantidad: int

    personalizacion: Optional[List[int]] = None


class DetallePedidoResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    pedido_id: int
    producto_id: int

    cantidad: int

    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal

    personalizacion: Optional[List[int]] = None