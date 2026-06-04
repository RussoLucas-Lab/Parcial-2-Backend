from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger


class Pago(SQLModel, table=True):
    """Modelo que representa un pago asociado a un pedido, incluyendo datos de MercadoPago."""
    __tablename__ = "pagos"

    # ── Datos locales del pago ──────────────────────────────────────────────
    id:         Optional[int] = Field(default=None, primary_key=True)
    pedido_id:  int           = Field(foreign_key="pedido.id", index=True)
    monto:      float         = Field(ge=0)

    # Estado local: mapeo simplificado de lo que devuelve MP.
    #   "pendiente" → arranca así; MP aún no confirmó
    #   "aprobado"  → MP dice status=approved
    #   "rechazado" → MP dice rejected/cancelled/refunded/charged_back
    estado:     str           = Field(max_length=20)

    # ── Datos de la PREFERENCIA (etapa 1 del flujo) ──────────────────────────
    # Se crean cuando el frontend pide "create-preference".
    # MP devuelve estos valores y los guardamos para tracking.

    # ID interno de MP para esta preferencia de pago.
    # Sirve para identificar el checkout en MP.
    mp_preference_id: Optional[str] = Field(default=None, max_length=255)

    # URL del checkout de MP a donde redirigir al usuario.
    # Es el link que el frontend usa para abrir el iframe/redirect.
    mp_init_point:    Optional[str] = Field(default=None, max_length=500)

    # ── Datos del PAGO REAL (etapa 4-5 del flujo) ────────────────────────────
    # Llegan via webhook cuando el usuario completa (o no) el pago en MP.

    # ID único del pago en MP (ej: 123456789). Se usa para consultar el estado.
    mp_payment_id:        Optional[int] = Field(default=None, sa_type=BigInteger)

    # ID de la orden en MP. Una orden puede agrupar múltiples pagos
    # (ej: si el usuario intenta pagar varias veces). Útil para reconciliación.
    mp_merchant_order_id: Optional[int] = Field(default=None, sa_type=BigInteger)

    # Estado CRUDO que devuelve MP: "approved", "rejected", "pending",
    # "in_process", "cancelled", "refunded", "charged_back".
    mp_status:            Optional[str] = Field(default=None, max_length=50)

    # Detalle adicional del estado en MP: "accredited", "pending_waiting_payment",
    # "pending_review_manual", etc. Nos sirve para debugging.
    mp_status_detail:     Optional[str] = Field(default=None, max_length=100)

    # ── Control de idempotencia ──────────────────────────────────────────────
    # UUID único por intento de pago. La constraint UNIQUE en la BD evita
    # que se creen registros duplicados si el frontend reenvía la misma solicitud
    # (ej: por un timeout de red).
    idempotency_key: str = Field(max_length=36, unique=True)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: datetime                  = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime]        = Field(default=None)