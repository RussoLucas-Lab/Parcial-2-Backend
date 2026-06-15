# =============================================================================
# test_estadisticas.py — Tests de integración: módulo de estadísticas
# =============================================================================
#
# Endpoints cubiertos (todos requieren rol ADMIN):
#   GET /estadisticas/facturacion-total     → suma total de pedidos activos
#   GET /estadisticas/cantidad-pedidos      → conteo de pedidos activos
#   GET /estadisticas/facturacion?periodo=X → facturación por día (semana/mes)
#   GET /estadisticas/pedidos?periodo=X     → pedidos por día (semana/mes)
#   GET /estadisticas/top-productos         → ranking de productos más vendidos
#
# NOTAS DE IMPLEMENTACIÓN:
#   - Todos los endpoints requieren rol ADMIN (require_role(["ADMIN"])).
#   - get_facturacion_total / get_cantidad_pedidos filtran por deleted_at IS NULL.
#     NO filtran por estado_codigo: CANCELADO y ENTREGADO se incluyen.
#   - test_ingresos_solo_approved y test_cancelado_no_suma están marcados
#     como xfail porque el backend actual no implementa esos filtros.
#   - La tabla Pago (MercadoPago) existe pero no tiene endpoint de estadísticas propio.
#
# =============================================================================

import pytest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.Pagos.models import Pago

from tests.conftest import _create_user, _do_login


# =============================================================================
# HELPERS INTERNOS
# =============================================================================

def _crear_pedido_db(db_session: Session, usuario_id: int, producto_id: int,
                     precio: Decimal = Decimal("500.00"), cantidad: int = 1,
                     estado: str = "PENDIENTE") -> int:
    """Helper para crear pedido directamente en BD y retornar su ID."""
    from app.modules.Pedido.model import Pedido
    from app.modules.DetallePedido.model import DetallePedido

    subtotal = precio * cantidad
    pedido = Pedido(
        usuario_id=usuario_id,
        forma_pago_codigo="EFECTIVO",
        estado_codigo=estado,
        subtotal=subtotal,
        descuento=Decimal("0.00"),
        costo_envio=Decimal("0.00"),
        total=subtotal,
    )
    db_session.add(pedido)
    db_session.flush()

    detalle = DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_id,
        cantidad=cantidad,
        nombre_snapshot="Producto Test",
        precio_snapshot=precio,
        subtotal_snap=subtotal,
    )
    db_session.add(detalle)
    db_session.flush()
    return pedido.id


def _get_admin_user_id(db_session: Session) -> int:
    from app.modules.Usuario.model import Usuario
    from sqlmodel import select
    u = db_session.exec(
        select(Usuario).where(Usuario.email == "admin_test@example.com")
    ).first()
    assert u is not None, "Usuario admin no encontrado. ¿Se ejecutó seed_data?"
    return u.id


# =============================================================================
# ACCESO Y PERMISOS
# =============================================================================

class TestEstadisticasAcceso:

    def test_estadisticas_requieren_admin(self, client: TestClient, seed_data):
        """Sin autenticación, todos los endpoints devuelven 401."""
        for endpoint in [
            "/estadisticas/facturacion-total",
            "/estadisticas/cantidad-pedidos",
            "/estadisticas/top-productos",
        ]:
            resp = client.get(endpoint)
            assert resp.status_code == 401, (
                f"Endpoint {endpoint} debería devolver 401 sin auth, "
                f"devolvió {resp.status_code}"
            )

    def test_estadisticas_rol_client_retorna_403(
        self,
        client: TestClient,
        client_headers: TestClient,
    ):
        """Usuario CLIENT no puede acceder a estadísticas (solo ADMIN)."""
        resp = client_headers.get("/estadisticas/facturacion-total")
        assert resp.status_code == 403

    def test_estadisticas_rol_pedidos_retorna_403(
        self,
        client: TestClient,
        pedidos_headers: TestClient,
    ):
        """Usuario PEDIDOS no puede acceder a estadísticas (solo ADMIN)."""
        resp = pedidos_headers.get("/estadisticas/facturacion-total")
        assert resp.status_code == 403


# =============================================================================
# FACTURACIÓN TOTAL Y CANTIDAD DE PEDIDOS
# =============================================================================

class TestResumen:

    def test_facturacion_total_con_pedidos(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        Con pedidos en BD, facturacion-total devuelve un valor >= 0.
        Verifica que el endpoint responde 200 y retorna un número válido.
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Paella", precio=750.00)
        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("750.00"), cantidad=2)

        # Act
        resp = admin_headers.get("/estadisticas/facturacion-total")

        # Assert
        assert resp.status_code == 200
        total = resp.json()
        assert total is not None
        assert Decimal(str(total)) >= Decimal("0")

    def test_cantidad_pedidos_con_pedidos(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        Con N pedidos en BD, cantidad-pedidos devuelve valor >= N.
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Risotto", precio=600.00)
        _crear_pedido_db(db_session, admin_id, producto.id)
        _crear_pedido_db(db_session, admin_id, producto.id)
        _crear_pedido_db(db_session, admin_id, producto.id)

        # Act
        resp = admin_headers.get("/estadisticas/cantidad-pedidos")

        # Assert
        assert resp.status_code == 200
        cantidad = resp.json()
        assert isinstance(cantidad, int)
        assert cantidad >= 3

    def test_facturacion_total_sin_pedidos(
        self,
        client: TestClient,
        admin_headers: TestClient,
        seed_data,
    ):
        """Sin pedidos en BD, facturacion-total devuelve 0."""
        resp = admin_headers.get("/estadisticas/facturacion-total")
        assert resp.status_code == 200
        assert Decimal(str(resp.json())) == Decimal("0")

    def test_cantidad_pedidos_sin_pedidos(
        self,
        client: TestClient,
        admin_headers: TestClient,
        seed_data,
    ):
        """Sin pedidos en BD, cantidad-pedidos devuelve 0."""
        resp = admin_headers.get("/estadisticas/cantidad-pedidos")
        assert resp.status_code == 200
        assert resp.json() == 0


# =============================================================================
# VENTAS POR PERÍODO
# =============================================================================

class TestVentasPorPeriodo:

    @pytest.mark.parametrize("periodo", ["semana", "mes"])
    def test_facturacion_por_periodo_retorna_lista(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
        periodo: str,
    ):
        """
        GET /estadisticas/facturacion?periodo=X devuelve una lista de
        {fecha, total} para los últimos X días.
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Ramen", precio=400.00)
        _crear_pedido_db(db_session, admin_id, producto.id)

        # Act
        resp = admin_headers.get(f"/estadisticas/facturacion?periodo={periodo}")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Si hay pedidos del día de hoy, debería haber al menos un registro
        for item in data:
            assert "fecha" in item
            assert "total" in item

    @pytest.mark.parametrize("periodo", ["semana", "mes"])
    def test_pedidos_por_periodo_retorna_lista(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
        periodo: str,
    ):
        """
        GET /estadisticas/pedidos?periodo=X devuelve lista de
        {fecha, cantidad} para los últimos X días.
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Ceviche", precio=350.00)
        _crear_pedido_db(db_session, admin_id, producto.id)
        _crear_pedido_db(db_session, admin_id, producto.id)

        # Act
        resp = admin_headers.get(f"/estadisticas/pedidos?periodo={periodo}")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert "fecha" in item
            assert "cantidad" in item

    def test_periodo_invalido_retorna_422(
        self,
        client: TestClient,
        admin_headers: TestClient,
        seed_data,
    ):
        """Periodo fuera de enum ('año') devuelve 422."""
        resp = admin_headers.get("/estadisticas/facturacion?periodo=año")
        assert resp.status_code == 422


# =============================================================================
# TOP PRODUCTOS
# =============================================================================

class TestTopProductos:

    def test_top_productos_retorna_lista(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        GET /estadisticas/top-productos devuelve lista de
        {producto, cantidad} ordenada de mayor a menor.
        """
        # Arrange: 2 productos con distintas cantidades vendidas
        admin_id = _get_admin_user_id(db_session)
        prod_a = producto_factory(nombre="Producto A", precio=100.00)
        prod_b = producto_factory(nombre="Producto B", precio=200.00)

        # Producto B vendido 3 veces, Producto A vendido 1 vez
        _crear_pedido_db(db_session, admin_id, prod_b.id, cantidad=3)
        _crear_pedido_db(db_session, admin_id, prod_a.id, cantidad=1)

        # Act
        resp = admin_headers.get("/estadisticas/top-productos")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # El primero debe ser Producto B (más vendido)
        nombres = [item["producto"] for item in data]
        cantidades = [item["cantidad"] for item in data]

        assert "Producto A" in nombres
        assert "Producto B" in nombres

        idx_a = nombres.index("Producto A")
        idx_b = nombres.index("Producto B")
        # Producto B (cantidad=3) debe aparecer antes que A (cantidad=1)
        assert cantidades[idx_b] > cantidades[idx_a]
        assert idx_b < idx_a, "Producto B debería tener mayor ranking que Producto A"

    def test_top_productos_sin_pedidos_retorna_lista_vacia(
        self,
        client: TestClient,
        admin_headers: TestClient,
        seed_data,
    ):
        """Sin pedidos, top-productos retorna lista vacía."""
        resp = admin_headers.get("/estadisticas/top-productos")
        assert resp.status_code == 200
        assert resp.json() == []


# =============================================================================
# PEDIDOS POR ESTADO
# =============================================================================

class TestPedidosPorEstado:

    def test_cantidad_pedidos_cuenta_todos_los_estados(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        cantidad-pedidos incluye pedidos en distintos estados.
        Nota: el endpoint actual no filtra por estado; cuenta todos.
        """
        # Arrange: pedidos en distintos estados
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory()

        _crear_pedido_db(db_session, admin_id, producto.id, estado="PENDIENTE")
        _crear_pedido_db(db_session, admin_id, producto.id, estado="CONFIRMADO")
        _crear_pedido_db(db_session, admin_id, producto.id, estado="ENTREGADO")
        _crear_pedido_db(db_session, admin_id, producto.id, estado="CANCELADO")

        # Act
        resp = admin_headers.get("/estadisticas/cantidad-pedidos")

        # Assert: todos los estados son contados (no hay filtro por estado en este endpoint)
        assert resp.status_code == 200
        cantidad = resp.json()
        assert cantidad >= 4


# =============================================================================
# INGRESOS POR ESTADO DE PAGO
# =============================================================================

class TestIngresosPorEstadoPago:

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "No existe endpoint de ingresos filtrado por estado de pago. "
            "get_facturacion_total suma Pedido.total sin filtrar por pagos aprobados. "
            "La tabla Pago existe pero no está integrada en las estadísticas. "
            "Implementar: filtrar pedidos por pago.estado == 'aprobado'."
        )
    )
    def test_ingresos_solo_approved(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        Los ingresos reportados deben incluir SOLO pagos aprobados.
        XFAIL: la implementación actual no filtra por estado de pago.
        """
        # Arrange
        import uuid
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Producto Pago", precio=1000.00)

        pedido_aprobado_id = _crear_pedido_db(
            db_session, admin_id, producto.id, Decimal("1000.00")
        )
        pedido_pendiente_id = _crear_pedido_db(
            db_session, admin_id, producto.id, Decimal("500.00")
        )
        pedido_rechazado_id = _crear_pedido_db(
            db_session, admin_id, producto.id, Decimal("300.00")
        )

        # Crear registros de pago con distintos estados
        pago_aprobado = Pago(
            pedido_id=pedido_aprobado_id, monto=1000.0,
            estado="aprobado", idempotency_key=str(uuid.uuid4())
        )
        pago_pendiente = Pago(
            pedido_id=pedido_pendiente_id, monto=500.0,
            estado="pendiente", idempotency_key=str(uuid.uuid4())
        )
        pago_rechazado = Pago(
            pedido_id=pedido_rechazado_id, monto=300.0,
            estado="rechazado", idempotency_key=str(uuid.uuid4())
        )
        db_session.add_all([pago_aprobado, pago_pendiente, pago_rechazado])
        db_session.flush()

        # Act
        resp = admin_headers.get("/estadisticas/facturacion-total")

        # Assert: solo el pago aprobado (1000) debería sumarse
        assert resp.status_code == 200
        total = Decimal(str(resp.json()))
        assert total == Decimal("1000.00"), (
            f"Se esperaba 1000.00 (solo aprobado). Recibido: {total}"
        )

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "get_facturacion_total suma Pedido.total sin filtrar por estado_codigo. "
            "Pedidos CANCELADOS son contabilizados en la facturación actual. "
            "Implementar filtro: .where(Pedido.estado_codigo.not_in(['CANCELADO']))"
        )
    )
    def test_cancelado_no_suma_en_facturacion(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        Pedido CANCELADO NO debe sumarse a la facturación total.
        XFAIL: la implementación actual incluye pedidos CANCELADOS en el total.
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Producto Cancelado", precio=9999.00)

        # Crear un pedido ENTREGADO (debe contarse)
        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("100.00"), estado="ENTREGADO")

        # Crear un pedido CANCELADO con monto alto (NO debe contarse)
        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("9999.00"), estado="CANCELADO")

        # Act
        resp = admin_headers.get("/estadisticas/facturacion-total")

        # Assert: solo el pedido ENTREGADO (100) debería sumarse
        assert resp.status_code == 200
        total = Decimal(str(resp.json()))
        assert total == Decimal("100.00"), (
            f"El pedido CANCELADO no debería sumar. "
            f"Total esperado: 100.00, recibido: {total}"
        )

    def test_facturacion_acumula_pedidos_activos(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        producto_factory,
    ):
        """
        Verificación positiva: la facturación acumula correctamente
        múltiples pedidos no eliminados (deleted_at IS NULL).
        """
        # Arrange
        admin_id = _get_admin_user_id(db_session)
        producto = producto_factory(nombre="Producto Activo", precio=200.00)

        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("200.00"))
        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("200.00"))
        _crear_pedido_db(db_session, admin_id, producto.id, Decimal("200.00"))

        # Act
        resp = admin_headers.get("/estadisticas/facturacion-total")

        # Assert: los 3 pedidos acumulan 600
        assert resp.status_code == 200
        total = Decimal(str(resp.json()))
        assert total >= Decimal("600.00")
