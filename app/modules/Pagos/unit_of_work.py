# app/modules/payments/unit_of_work.py — Unit of Work específico para pagos
#
# Cada operación de pago (crear, actualizar por webhook, confirmar) necesita
# ser transaccional: si algo falla a medio camino, no queremos datos inconsistentes
# entre la tabla de pagos y la de pedidos.
#
from sqlmodel import Session
from app.Core.unit_of_work import UnitOfWork
from app.modules.Pagos.repository import PagoRepository


class PagoUnitOfWork(UnitOfWork):
    """Unit of Work que expone el repositorio de pagos dentro de una transacción."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pagos = PagoRepository(session)
