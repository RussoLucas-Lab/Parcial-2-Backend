# app/modules/payments/schemas.py — Esquemas Pydantic para pagos
#
# Define los contratos de entrada/salida de la API de pagos.
# Son los DTOs (Data Transfer Objects) que viajan entre el frontend y
# nuestra API, y entre nuestra API y MercadoPago.
#
from typing import Optional
from sqlmodel import SQLModel, Field


class CrearPagoRequest(SQLModel):
    """
    Body que envía el frontend para iniciar un pago.
    Solo necesita el ID del pedido — el monto lo tomamos de nuestra BD
    para evitar que el cliente manipule el precio.
    """
    pedido_id: int = Field(..., description="ID del pedido a pagar")


class ConfirmarPagoRequest(SQLModel):
    """
    Body para consultar/confirmar el estado de un pago.
    El payment_id es el ID que MP asigna al pago real. Si no se envía,
    el sistema busca el último pago asociado al pedido en nuestra BD.
    """
    pedido_id:  int = Field(..., description="ID del pedido")
    payment_id: Optional[int] = Field(default=None, description="ID del pago en MP")


class PagoCrearResponse(SQLModel):
    """
    Respuesta después de crear la preferencia en MP.

    El frontend usa estos datos para:
    - preference_id: identificar la preferencia (útil para tracking)
    - init_point:    URL del checkout de MP (abre el iframe o redirect)
    - public_key:    clave pública de MP (para el frontend SDK de MP)

    Ejemplo de uso en frontend React:
      window.MercadoPago(public_key).checkout({ preference: { id: preference_id } })
    """
    pago_id:       int
    preference_id: str
    init_point:    Optional[str] = None
    public_key:    Optional[str] = None


class PagoEstadoResponse(SQLModel):
    """
    Respuesta con el estado actual del pago.
    El frontend usa esto para mostrar al usuario si su pago fue exitoso o no.
    """
    estado:     Optional[str] = None  # "pendiente" | "aprobado" | "rechazado" | None
    pedido_id:  int
