from sqlmodel import Session

from app.Core.unit_of_work import UnitOfWork

from app.modules.DetallePedido.repository import DetallePedidoRepository
from app.modules.Producto.repository import ProductoRepository
from app.modules.Pedido.repository import PedidoRepository


class DetallePedidoUnitOfWork(UnitOfWork):

    def __init__(self, session: Session):
        super().__init__(session)

        self.detalles = DetallePedidoRepository(session)
        self.productos = ProductoRepository(session)
        self.pedidos = PedidoRepository(session)
        