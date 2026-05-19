from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ── Entrada ───────────────────────────────────────────────────────────────────

class PedidoDetalleInput(BaseModel):
    producto_id: int
    cantidad: int
    personalizacion: Optional[List[int]] = None


class PedidoCreate(BaseModel):
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    notas: Optional[str] = None

    detalles: List[PedidoDetalleInput]



# ── Salida ───────────────────────────────────────────────────────────────────

class PedidoResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    direccion_id: Optional[int]
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str]