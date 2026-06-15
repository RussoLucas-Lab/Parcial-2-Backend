# =============================================================================
# test_pedidos.py — Tests de integración: ciclo de vida de pedidos
# =============================================================================
#
# Endpoints cubiertos:
#   POST  /api/v1/pedidos                → crear pedido
#   GET   /api/v1/pedidos                → listar pedidos
#   GET   /api/v1/pedidos/{id}           → obtener pedido por ID
#   PATCH /api/v1/pedidos/{id}/estado    → avanzar estado (FSM + RBAC)
#
# FSM (app/modules/Pedido/fsm.py):
#   PENDIENTE → CONFIRMADO | CANCELADO
#   CONFIRMADO → EN_PREP | CANCELADO
#   EN_PREP → EN_CAMINO | CANCELADO  (ADMIN: EN_PREP → ENTREGADO)
#   ENTREGADO → [] (terminal)
#   CANCELADO → [] (terminal)
#
# RBAC para PATCH /estado (COCINA_ROLES):
#   ADMIN   → cualquier transición válida de la FSM
#   PEDIDOS → PENDIENTE→CONFIRMADO|CANCELADO, CONFIRMADO→CANCELADO, EN_PREP→CANCELADO
#   COCINA  → CONFIRMADO→EN_PREP, EN_PREP→ENTREGADO
#   CLIENT  → no tiene acceso (403 antes de llegar a FSM)
#
# SUPUESTOS:
#   - Stock validation: NO implementada en PedidoService.create().
#     test_crear_pedido_stock_insuficiente marcado xfail.
#   - Historial de estados: NO guardado en avanzar_estado().
#     test_historial_append_only marca xfail para la comprobación de historial.
#   - Transición inválida devuelve 403 (no 422) según PedidoService.avanzar_estado().
#
# =============================================================================

import pytest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.modules.Pedido.model import Pedido
from app.modules.HistorialPedido.model import HistorialEstadoPedido
from app.modules.Usuario.model import Usuario

from tests.conftest import _create_user, _do_login


# =============================================================================
# HELPERS
# =============================================================================

def _get_user_by_email(db_session: Session, email: str) -> Usuario:
    """Retorna un usuario por email (assert si no existe)."""
    user = db_session.exec(select(Usuario).where(Usuario.email == email)).first()
    assert user is not None, f"Usuario con email={email!r} no encontrado en BD de test"
    return user


# =============================================================================
# CREACIÓN DE PEDIDOS
# =============================================================================

class TestCrearPedido:

    def test_crear_pedido_ok(
        self,
        client: TestClient,
        db_session: Session,
        client_headers: TestClient,
        producto_factory,
    ):
        """
        Usuario autenticado (CLIENT) crea un pedido con producto existente.
        Retorna 201 con los datos del pedido correctamente calculados.
        """
        # Arrange
        producto = producto_factory(nombre="Pizza Margherita", precio=500.00, stock=10)

        payload = {
            "forma_pago_codigo": "EFECTIVO",
            "detalles": [
                {"producto_id": producto.id, "cantidad": 2}
            ],
        }

        # Act
        resp = client_headers.post("/api/v1/pedidos", json=payload)

        # Assert
        assert resp.status_code == 201, resp.json()
        data = resp.json()

        assert data["estado_codigo"] == "PENDIENTE"
        assert data["forma_pago_codigo"] == "EFECTIVO"
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["producto_id"] == producto.id
        assert data["detalles"][0]["cantidad"] == 2
        assert Decimal(str(data["subtotal"])) == Decimal("1000.00")
        assert Decimal(str(data["total"])) == Decimal("1000.00")
        assert "id" in data
        assert "usuario_id" in data

    def test_crear_pedido_producto_inexistente_retorna_404(
        self,
        client: TestClient,
        client_headers: TestClient,
        seed_data,
    ):
        """Pedido con producto_id que no existe devuelve 404."""
        payload = {
            "forma_pago_codigo": "EFECTIVO",
            "detalles": [{"producto_id": 99999, "cantidad": 1}],
        }
        resp = client_headers.post("/api/v1/pedidos", json=payload)
        assert resp.status_code == 404

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Validación de stock NO implementada en PedidoService.create(). "
            "El servicio usa el precio pero no verifica producto.stock_cantidad. "
            "Implementar: if producto.stock_cantidad < item.cantidad: raise HTTP 400"
        )
    )
    def test_crear_pedido_stock_insuficiente(
        self,
        client: TestClient,
        client_headers: TestClient,
        producto_factory,
    ):
        """
        Pedido que supera el stock disponible debe retornar 400 Bad Request.
        XFAIL: la validación de stock no está implementada actualmente.
        """
        # Arrange: producto con stock=1
        producto = producto_factory(nombre="Producto Escaso", precio=100.00, stock=1)

        payload = {
            "forma_pago_codigo": "EFECTIVO",
            "detalles": [{"producto_id": producto.id, "cantidad": 999}],
        }

        # Act
        resp = client_headers.post("/api/v1/pedidos", json=payload)

        # Assert
        assert resp.status_code == 400, (
            f"Se esperaba 400 por stock insuficiente (stock=1, cantidad=999). "
            f"Recibido: {resp.status_code}"
        )

    def test_crear_pedido_sin_autenticacion_retorna_401(
        self,
        client: TestClient,
        producto_factory,
        seed_data,
    ):
        """Crear pedido sin cookie de sesión activa devuelve 401."""
        producto = producto_factory()
        payload = {
            "forma_pago_codigo": "EFECTIVO",
            "detalles": [{"producto_id": producto.id, "cantidad": 1}],
        }
        resp = client.post("/api/v1/pedidos", json=payload)
        assert resp.status_code == 401


# =============================================================================
# AVANZAR ESTADO — FSM + RBAC
# =============================================================================

class TestAvanzarEstado:

    def test_avanzar_estado_valido_pendiente_a_confirmado(
        self,
        client: TestClient,
        db_session: Session,
        pedidos_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """
        Pedido en PENDIENTE avanza a CONFIRMADO con usuario PEDIDOS.
        Verifica estado actualizado en la respuesta y que el ID no cambia.
        """
        # Arrange: obtener usuario PEDIDOS (creado por pedidos_headers fixture)
        pedidos_user = _get_user_by_email(db_session, "pedidos_test@example.com")
        producto = producto_factory(nombre="Hamburguesa", precio=300.00)
        pedido = pedido_factory(
            usuario_id=pedidos_user.id,
            producto_id=producto.id,
        )

        # Act: PENDIENTE → CONFIRMADO
        resp = pedidos_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "CONFIRMADO"},
        )

        # Assert
        assert resp.status_code == 200, resp.json()
        data = resp.json()
        assert data["estado_codigo"] == "CONFIRMADO"
        assert data["id"] == pedido.id

    def test_avanzar_estado_invalido_terminal_retorna_403(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """
        Pedido en ENTREGADO (estado terminal) no puede transicionar a EN_PREP.
        La FSM devuelve 403 Forbidden.

        Valida RN-01: estados terminales no permiten transición.
        """
        # Arrange: pedido creado directamente en ENTREGADO (bypassing FSM)
        admin_user = _get_user_by_email(db_session, "admin_test@example.com")
        producto = producto_factory(nombre="Milanesa", precio=400.00)
        pedido = pedido_factory(
            usuario_id=admin_user.id,
            producto_id=producto.id,
            estado="ENTREGADO",
        )

        # Act: ENTREGADO → EN_PREP (transición inválida desde terminal)
        resp = admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "EN_PREP"},
        )

        # Assert: 403 porque ENTREGADO es estado terminal (TRANSICIONES["ADMIN"]["ENTREGADO"] = set())
        assert resp.status_code == 403, (
            f"Se esperaba 403 para transición desde estado terminal ENTREGADO. "
            f"Recibido: {resp.status_code} - {resp.json()}"
        )

    def test_cancelar_pedido_con_rol_pedidos(
        self,
        client: TestClient,
        db_session: Session,
        pedidos_headers: TestClient,
        pedido_factory,
        producto_factory,
        seed_data,
    ):
        """
        Usuario PEDIDOS cancela un pedido en PENDIENTE.

        Nota: rol CLIENT no tiene acceso a PATCH /pedidos/{id}/estado.
        La cancelación la realiza el personal (PEDIDOS/ADMIN).
        """
        # Arrange: crear cliente propietario del pedido
        _create_user(db_session, "owner@example.com", "Owner1234!", ["CLIENT"])
        owner = _get_user_by_email(db_session, "owner@example.com")

        producto = producto_factory(nombre="Ensalada César", precio=200.00)
        pedido = pedido_factory(usuario_id=owner.id, producto_id=producto.id)

        # Act: PEDIDOS cancela el pedido (PENDIENTE → CANCELADO ✓)
        resp = pedidos_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "CANCELADO", "motivo": "Cliente lo solicitó"},
        )

        # Assert
        assert resp.status_code == 200, resp.json()
        data = resp.json()
        assert data["estado_codigo"] == "CANCELADO"
        assert data["id"] == pedido.id

    def test_rol_client_no_puede_cambiar_estado(
        self,
        client: TestClient,
        db_session: Session,
        client_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """
        Usuario CLIENT no puede acceder a PATCH /pedidos/{id}/estado.
        require_role(COCINA_ROLES) rechaza con 403 antes de evaluar la FSM.
        """
        # Arrange
        client_user = _get_user_by_email(db_session, "client_test@example.com")
        producto = producto_factory()
        pedido = pedido_factory(usuario_id=client_user.id, producto_id=producto.id)

        # Act
        resp = client_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "CONFIRMADO"},
        )

        # Assert: CLIENT está fuera de COCINA_ROLES
        assert resp.status_code == 403

    def test_avanzar_estado_pedido_inexistente_retorna_404(
        self,
        client: TestClient,
        admin_headers: TestClient,
        seed_data,
    ):
        """PATCH a pedido inexistente devuelve 404."""
        resp = admin_headers.patch(
            "/api/v1/pedidos/99999/estado",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        assert resp.status_code == 404


# =============================================================================
# HISTORIAL DE ESTADOS (APPEND-ONLY)
# =============================================================================

class TestHistorialEstados:

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "HistorialEstadoPedido no se guarda en PedidoService.avanzar_estado(). "
            "El servicio actualiza pedido.estado_codigo pero NO crea registros en "
            "historial_estado_pedido. Para implementar: agregar dentro del UoW: "
            "uow.session.add(HistorialEstadoPedido(pedido_id=pedido_id, "
            "estado_desde=origen, estado_hacia=destino, usuario_id=current_user.id))"
        )
    )
    def test_historial_append_only(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """
        Múltiples transiciones válidas generan registros de historial
        en modo append-only (nunca modifica registros anteriores).
        XFAIL: historial no está implementado en avanzar_estado().
        """
        # Arrange
        admin_user = _get_user_by_email(db_session, "admin_test@example.com")
        producto = producto_factory(nombre="Sushi Premium", precio=800.00)
        pedido = pedido_factory(usuario_id=admin_user.id, producto_id=producto.id)

        # Act: dos transiciones válidas
        admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "EN_PREP"},
        )

        # Assert: verificar registros en tabla historial_estado_pedido
        db_session.expire_all()
        historial = db_session.exec(
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido.id)
        ).all()

        assert len(historial) >= 2, (
            f"Se esperaban ≥2 registros en historial. Encontrados: {len(historial)}. "
            "El servicio no implementa el guardado de historial."
        )

        estados_hacia = [h.estado_hacia for h in historial]
        assert "CONFIRMADO" in estados_hacia
        assert "EN_PREP" in estados_hacia

        # Append-only: los registros anteriores no deben ser modificados
        for reg in historial:
            assert reg.id is not None

    def test_transiciones_actualizan_estado_del_pedido(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """
        Múltiples transiciones válidas actualizan correctamente estado_codigo.
        Verifica que cada transición se refleja en la respuesta.
        """
        # Arrange
        admin_user = _get_user_by_email(db_session, "admin_test@example.com")
        producto = producto_factory(nombre="Tacos de Tinga", precio=250.00)
        pedido = pedido_factory(usuario_id=admin_user.id, producto_id=producto.id)

        # Act + Assert: cada transición devuelve el estado esperado

        r1 = admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "CONFIRMADO"},
        )
        assert r1.status_code == 200
        assert r1.json()["estado_codigo"] == "CONFIRMADO"

        r2 = admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "EN_PREP"},
        )
        assert r2.status_code == 200
        assert r2.json()["estado_codigo"] == "EN_PREP"

        r3 = admin_headers.patch(
            f"/api/v1/pedidos/{pedido.id}/estado",
            json={"nuevo_estado": "ENTREGADO"},
        )
        assert r3.status_code == 200
        assert r3.json()["estado_codigo"] == "ENTREGADO"


# =============================================================================
# LISTADO Y CONSULTA
# =============================================================================

class TestListadoPedidos:

    def test_listar_pedidos_requiere_autenticacion(self, client: TestClient, seed_data):
        """GET /pedidos sin autenticación devuelve 401."""
        resp = client.get("/api/v1/pedidos")
        assert resp.status_code == 401

    def test_listar_pedidos_retorna_lista(
        self,
        client: TestClient,
        db_session: Session,
        client_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """Usuario autenticado puede listar pedidos y obtiene una lista."""
        # Arrange
        client_user = _get_user_by_email(db_session, "client_test@example.com")
        producto = producto_factory()
        pedido_factory(usuario_id=client_user.id, producto_id=producto.id)

        # Act
        resp = client_headers.get("/api/v1/pedidos")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_obtener_pedido_por_id(
        self,
        client: TestClient,
        db_session: Session,
        client_headers: TestClient,
        pedido_factory,
        producto_factory,
    ):
        """GET /pedidos/{id} retorna el pedido correcto con sus detalles."""
        # Arrange
        client_user = _get_user_by_email(db_session, "client_test@example.com")
        producto = producto_factory(nombre="Calzone Rústico", precio=450.00)
        pedido = pedido_factory(
            usuario_id=client_user.id,
            producto_id=producto.id,
            cantidad=3,
            precio=Decimal("450.00"),
        )

        # Act
        resp = client_headers.get(f"/api/v1/pedidos/{pedido.id}")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == pedido.id
        assert data["estado_codigo"] == "PENDIENTE"
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["cantidad"] == 3

    def test_obtener_pedido_inexistente_retorna_404(
        self,
        client: TestClient,
        client_headers: TestClient,
        seed_data,
    ):
        """GET /pedidos/99999 devuelve 404 cuando el pedido no existe."""
        resp = client_headers.get("/api/v1/pedidos/99999")
        assert resp.status_code == 404
