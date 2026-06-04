# app/modules/payments/repository.py — Repositorio de pagos
#
# Además del CRUD básico, agrega métodos de búsqueda especializados para
# los distintos IDs que maneja MercadoPago:
#   - mp_payment_id:        ID del pago en MP (individual)
#   - mp_merchant_order_id: ID de la orden en MP (puede agrupar varios pagos)
#   - idempotency_key:      clave única para evitar duplicados
#
from typing import Optional, List
from sqlmodel import Session, select
from app.Core.repository import BaseRepository
from app.modules.Pagos.models import Pago


class PagoRepository(BaseRepository[Pago]):
    """Repositorio de pagos con métodos de búsqueda específicos de MP."""

    def __init__(self, session: Session):
        super().__init__(session, Pago)

    def get_by_pedido(self, pedido_id: int) -> List[Pago]:
        """
        Retorna todos los pagos de un pedido, ordenados del más reciente al más viejo.
        Útil para ver el historial de intentos de pago de un pedido.
        """
        return list(
            self.session.exec(
                select(Pago)
                .where(Pago.pedido_id == pedido_id)
                .order_by(Pago.created_at.desc())
            ).all()
        )

    def get_ultimo_by_pedido(self, pedido_id: int) -> Optional[Pago]:
        """
        Retorna el último intento de pago de un pedido.
        Se usa para consultar el estado más reciente sin conocer el payment_id de MP.
        """
        pagos = self.get_by_pedido(pedido_id)
        return pagos[0] if pagos else None

    def get_by_idempotency_key(self, key: str) -> Optional[Pago]:
        """
        Busca un pago por su clave de idempotencia.
        Sirve para evitar crear pagos duplicados si el frontend reenvía la misma
        solicitud (ej: por timeout de red, doble click en el botón, etc.).
        """
        return self.session.exec(
            select(Pago).where(Pago.idempotency_key == key)
        ).first()

    def get_by_mp_payment_id(self, mp_payment_id: int) -> Optional[Pago]:
        """
        Busca un pago por el ID que MP asignó al pago real.
        Es el método principal para correlacionar notificaciones del webhook
        con nuestros registros locales.
        """
        return self.session.exec(
            select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        ).first()

    def get_by_mp_merchant_order_id(self, merchant_order_id: int) -> Optional[Pago]:
        """
        Busca un pago por el ID de orden de MP.
        Una merchant_order puede contener múltiples pagos (ej: el usuario
        intenta pagar varias veces). Se usa como fallback cuando no encontramos
        el pago por mp_payment_id directo.
        """
        return self.session.exec(
            select(Pago).where(Pago.mp_merchant_order_id == merchant_order_id)
        ).first()
