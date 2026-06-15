# =============================================================================
# conftest.py — Configuración global de tests de integración
# =============================================================================
#
# ORDEN CRÍTICO DE IMPORTS:
#   1. Patches deben ejecutarse ANTES de importar cualquier módulo de la app
#   2. Sin esto, los tipos PostgreSQL-específicos (ARRAY) rompen SQLite
#
# =============================================================================

import os
# Las cookies con secure=True no se envían en HTTP (TestClient usa http://testserver).
# Esto permite que las cookies funcionen correctamente en tests.
os.environ.setdefault("COOKIE_SECURE", "False")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 1: Reemplazar ARRAY de PostgreSQL con JSON compatible con SQLite
# Debe ir ANTES de cualquier import de la app
# ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy.types import JSON as _JSONType
import sqlalchemy.dialects.postgresql as _pg_dialect


class _ARRAYCompat(_JSONType):
    """
    Sustituye ARRAY de PostgreSQL para usar JSON en SQLite durante tests.
    Almacena listas como JSON text; round-trips correctamente para tests.
    """
    def __init__(self, item_type=None, as_tuple=False, dimensions=None,
                 zero_indexes=False, **kw):
        super().__init__()


_pg_dialect.ARRAY = _ARRAYCompat

# ─────────────────────────────────────────────────────────────────────────────
# Imports estándar — DESPUÉS del patch
# ─────────────────────────────────────────────────────────────────────────────
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Imports de la app (ahora seguros porque ARRAY ya fue parcheado)
from app.main import app
from app.Core.database import get_session
from app.Core.security import hash_password
from app.modules.EstadoPedido.model import EstadoPedido
from app.modules.FormaPago.model import FormaPago
from app.modules.Pedido.model import Pedido
from app.modules.DetallePedido.model import DetallePedido
from app.modules.Producto.model import Producto
from app.modules.Rol.model import Rol
from app.modules.Usuario.model import Usuario, UsuarioRol
from app.modules.Usuario.unit_of_work import UsuarioUnitOfWork, get_usuario_uow


# =============================================================================
# FIXTURES DE BASE DE DATOS
# =============================================================================

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Crea un engine SQLite in-memory nuevo para cada test.
    Garantiza aislamiento total: cada test tiene su propia BD independiente.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


# =============================================================================
# FIXTURE DE CLIENTE HTTP
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    TestClient con:
    - get_session sobreescrito para usar SQLite de test
    - get_usuario_uow sobreescrito para autenticación en el mismo scope
    - Startup de PostgreSQL desactivado
    """
    def override_get_session():
        yield db_session

    def override_get_usuario_uow():
        yield UsuarioUnitOfWork(db_session)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_usuario_uow] = override_get_usuario_uow

    # Deshabilitar startup event (evita intento de conexión a PostgreSQL)
    saved_startup = list(getattr(app.router, "on_startup", []))
    saved_shutdown = list(getattr(app.router, "on_shutdown", []))
    if hasattr(app.router, "on_startup"):
        app.router.on_startup.clear()
    if hasattr(app.router, "on_shutdown"):
        app.router.on_shutdown.clear()

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    # Restaurar handlers originales
    if hasattr(app.router, "on_startup"):
        app.router.on_startup.extend(saved_startup)
    if hasattr(app.router, "on_shutdown"):
        app.router.on_shutdown.extend(saved_shutdown)

    app.dependency_overrides.clear()


# =============================================================================
# HELPERS DE SEED
# =============================================================================

def _seed_base_data(session: Session) -> None:
    """Siembra roles, estados de pedido y formas de pago requeridos."""

    roles = [
        Rol(codigo="ADMIN",   nombre="Administrador"),
        Rol(codigo="CLIENT",  nombre="Cliente"),
        Rol(codigo="PEDIDOS", nombre="Pedidos"),
        Rol(codigo="COCINA",  nombre="Cocina"),
        Rol(codigo="STOCK",   nombre="Stock"),
    ]
    for rol in roles:
        if not session.get(Rol, rol.codigo):
            session.add(rol)

    estados = [
        EstadoPedido(codigo="PENDIENTE",  descripcion="Pendiente",     orden=1, es_terminal=False),
        EstadoPedido(codigo="CONFIRMADO", descripcion="Confirmado",    orden=2, es_terminal=False),
        EstadoPedido(codigo="EN_PREP",    descripcion="En preparación",orden=3, es_terminal=False),
        EstadoPedido(codigo="EN_CAMINO",  descripcion="En camino",     orden=4, es_terminal=False),
        EstadoPedido(codigo="ENTREGADO",  descripcion="Entregado",     orden=5, es_terminal=True),
        EstadoPedido(codigo="CANCELADO",  descripcion="Cancelado",     orden=6, es_terminal=True),
    ]
    for ep in estados:
        if not session.get(EstadoPedido, ep.codigo):
            session.add(ep)

    formas_pago = [
        FormaPago(codigo="EFECTIVO",      descripcion="Pago en efectivo"),
        FormaPago(codigo="TARJETA",       descripcion="Tarjeta de crédito"),
        FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia bancaria"),
    ]
    for fp in formas_pago:
        if not session.get(FormaPago, fp.codigo):
            session.add(fp)

    session.flush()


def _create_user(
    session: Session,
    email: str,
    password: str,
    roles: list[str],
    nombre: str = "Test",
    apellido: str = "User",
) -> Usuario:
    """Crea un usuario con los roles indicados en la sesión de test."""
    usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        email=email,
        password_hash=hash_password(password),
    )
    session.add(usuario)
    session.flush()
    for rol_codigo in roles:
        session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo=rol_codigo))
    session.flush()
    return usuario


def _do_login(test_client: TestClient, email: str, password: str) -> TestClient:
    """
    Realiza login y retorna el mismo cliente (las cookies quedan en su jar).
    """
    resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login falló: {resp.json()}"
    return test_client


# =============================================================================
# FIXTURE DE SEED DATA (se llama en cada test que lo necesite)
# =============================================================================

@pytest.fixture(scope="function")
def seed_data(db_session: Session) -> None:
    """Siembra datos base: roles, estados de pedido, formas de pago."""
    _seed_base_data(db_session)


# =============================================================================
# FIXTURES DE AUTENTICACIÓN POR ROL
# =============================================================================

@pytest.fixture(scope="function")
def admin_headers(db_session: Session, client: TestClient, seed_data):
    """
    Crea un usuario ADMIN, realiza login y retorna el cliente autenticado.
    Los tokens viajan en cookies HTTPOnly dentro del TestClient.
    """
    email, password = "admin_test@example.com", "Admin1234!"
    _create_user(db_session, email, password, ["ADMIN"])
    return _do_login(client, email, password)


@pytest.fixture(scope="function")
def client_headers(db_session: Session, client: TestClient, seed_data):
    """Crea usuario CLIENT y retorna el cliente autenticado."""
    email, password = "client_test@example.com", "Client1234!"
    _create_user(db_session, email, password, ["CLIENT"])
    return _do_login(client, email, password)


@pytest.fixture(scope="function")
def pedidos_headers(db_session: Session, client: TestClient, seed_data):
    """Crea usuario PEDIDOS y retorna el cliente autenticado."""
    email, password = "pedidos_test@example.com", "Pedidos1234!"
    _create_user(db_session, email, password, ["PEDIDOS"])
    return _do_login(client, email, password)


# =============================================================================
# FACTORIES
# =============================================================================

@pytest.fixture(scope="function")
def producto_factory(db_session: Session, seed_data):
    """
    Factory para crear productos válidos en la BD de test.
    Parámetros configurables: nombre, precio, stock.
    """
    def _make(
        nombre: str = "Producto Test",
        precio: float = 100.00,
        stock: int = 10,
    ) -> Producto:
        producto = Producto(
            nombre=nombre,
            precio_base=Decimal(str(precio)),
            imagenes_url=[],
            stock_cantidad=stock,
            disponible=True,
        )
        db_session.add(producto)
        db_session.flush()
        db_session.refresh(producto)
        return producto

    return _make


@pytest.fixture(scope="function")
def pedido_factory(db_session: Session, seed_data):
    """
    Factory para crear pedidos directamente en BD (sin pasar por la API).
    Crea el Pedido + DetallePedido en estado PENDIENTE.
    """
    def _make(
        usuario_id: int,
        producto_id: int,
        cantidad: int = 1,
        nombre_producto: str = "Producto Test",
        precio: Decimal = Decimal("100.00"),
        estado: str = "PENDIENTE",
    ) -> Pedido:
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
            nombre_snapshot=nombre_producto,
            precio_snapshot=precio,
            subtotal_snap=subtotal,
        )
        db_session.add(detalle)
        db_session.flush()
        db_session.refresh(pedido)

        return pedido

    return _make
