from sqlmodel import Session

from app.Core.unit_of_work import UnitOfWork

from app.modules.Producto.repository import ProductoRepository
from app.modules.Categoria.repository import CategoriaRepository
from app.modules.Pedido.repository import PedidoRepository
from app.modules.DetallePedido.repository import DetallePedidoRepository
from app.modules.Pagos.repository import PagoRepository

class EstadisticaUnitOfWork(UnitOfWork):

    def __init__(self, session: Session):
        super().__init__(session)

        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        self.pedidos = PedidoRepository(session)
        self.detalles_pedido = DetallePedidoRepository(session)
        self.pagos = PagoRepository(session)