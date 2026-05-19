from sqlmodel import Session

from app.Core.unit_of_work import UnitOfWork

from app.modules.Pedido.repository import PedidoRepository
from app.modules.DetallePedido.repository import DetallePedidoRepository
from app.modules.HistorialPedido.repository import HistorialEstadoPedidoRepository
from app.modules.EstadoPedido.repository import EstadoPedidoRepository
from app.modules.FormaPago.repository import FormaPagoRepository
from app.modules.Producto.repository import ProductoRepository


class PedidoUnitOfWork(UnitOfWork):

    def __init__(self, session: Session):
        super().__init__(session)

        self.pedidos = PedidoRepository(session)
        self.detalles = DetallePedidoRepository(session)
        self.historial = HistorialEstadoPedidoRepository(session)
        
        self.productos = ProductoRepository(session)

        self.estados = EstadoPedidoRepository(session)
        self.formas_pago = FormaPagoRepository(session)