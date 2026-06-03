from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel, Field


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

class PedidoEstadoUpdate(SQLModel):
    # Datos de entrada para avanzar el estado de un pedido en la FSM
    nuevo_estado: str        = Field(min_length=1, max_length=50)
    motivo:       str | None = Field(default=None, max_length=200)


# ── Salida ───────────────────────────────────────────────────────────────────

class DetallePedidoResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal

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

    detalles: list[DetallePedidoResponse]


class PedidoPublic(BaseModel):

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

    detalles: list[DetallePedidoResponse]