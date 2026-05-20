from decimal import Decimal
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.DetallePedido.model import DetallePedido
from app.modules.Pedido.fsm import TRANSICIONES_PEDIDO
from app.modules.Pedido.model import Pedido
from app.modules.Pedido.schemas import PedidoCreate, PedidoResponse
from app.modules.Pedido.unit_of_work import PedidoUnitOfWork

from app.modules.HistorialPedido.model import HistorialEstadoPedido

class PedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _validate_transition(self, estado_actual: str, nuevo_estado: str):

        permitidos = TRANSICIONES_PEDIDO.get(estado_actual, [])

        if nuevo_estado not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede pasar de {estado_actual} a {nuevo_estado}"
            )


    def _get_producto_or_404(self, uow, producto_id: int):
        producto = uow.productos.get_by_id(producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {producto_id} no encontrado"
            )
        return producto

    def _get_pedido_or_404(self, uow, pedido_id: int) -> Pedido:
        pedido = uow.pedidos.get_by_id(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido {pedido_id} no encontrado"
            )
        return pedido

    def list_all(self):
        with PedidoUnitOfWork(self._session) as uow:
            pedidos = uow.pedidos.get_all()
            return pedidos   

    def create(self, data: PedidoCreate, usuario_id: int) -> PedidoResponse:

        with PedidoUnitOfWork(self._session) as uow:

            estado_inicial = "PENDIENTE"

            pedido = Pedido(
                usuario_id=usuario_id,
                direccion_id=data.direccion_id,
                estado_codigo=estado_inicial,
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=Decimal("0.00"),
                descuento=Decimal("0.00"),
                costo_envio=Decimal("50.00"),
                total=Decimal("0.00"),
                notas=data.notas,
                activo=True
            )

            uow.pedidos.add(pedido)
            uow.session.flush()

            subtotal_total = Decimal("0.00")

            for item in data.detalles:

                producto = self._get_producto_or_404(uow, item.producto_id)

                precio = Decimal(producto.precio_base)
                subtotal = precio * item.cantidad

                subtotal_total += subtotal

                uow.detalles.add(
                    DetallePedido(
                        pedido_id=pedido.id,
                        producto_id=producto.id,
                        cantidad=item.cantidad,
                        nombre_snapshot=producto.nombre,
                        precio_snapshot=precio,
                        subtotal_snap=subtotal,
                        personalizacion=item.personalizacion
                    )
                )

            total = subtotal_total + pedido.costo_envio - pedido.descuento

            pedido.subtotal = subtotal_total
            pedido.total = total

            
            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=None,
                    estado_hacia=estado_inicial,
                    usuario_id=usuario_id
                )
            )

            uow.pedidos.add(pedido)

            return PedidoResponse.model_validate(
                pedido,
                from_attributes=True
            )


    def cambiar_estado(
        self,
        pedido_id: int,
        nuevo_estado: str,
        usuario_id: int
    ) -> PedidoResponse:

        with PedidoUnitOfWork(self._session) as uow:

            pedido = self._get_pedido_or_404(uow, pedido_id)

            estado_actual = pedido.estado_codigo

            
            self._validate_transition(estado_actual, nuevo_estado)

            
            pedido.estado_codigo = nuevo_estado

            uow.pedidos.add(pedido)

            
            uow.historial.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_actual,
                    estado_hacia=nuevo_estado,
                    usuario_id=usuario_id
                )
            )

            return PedidoResponse.model_validate(
                pedido,
                from_attributes=True
            )

    def get_by_usuario(self, usuario_id: int):
        with PedidoUnitOfWork(self._session) as uow:
            pedidos = uow.pedidos.get_by_usuario(usuario_id)
            return pedidos

    def get_by_id(self, pedido_id: int) -> PedidoResponse:

        

        with PedidoUnitOfWork(self._session) as uow:

            pedido = self._get_pedido_or_404(uow, pedido_id)

            return PedidoResponse.model_validate(
                pedido,
                from_attributes=True
            )

    def soft_delete(self, pedido_id: int) -> None:

        with PedidoUnitOfWork(self._session) as uow:

            pedido = self._get_pedido_or_404(uow, pedido_id)

            pedido.activo = False

            uow.pedidos.add(pedido)