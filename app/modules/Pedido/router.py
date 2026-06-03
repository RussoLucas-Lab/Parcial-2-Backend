# =============================================================================
# ROUTER — Pedidos + WebSocket (Rooms por Rol y por Pedido)
# =============================================================================
#
# Este módulo define los endpoints HTTP (REST) y el WebSocket para la gestión
# de pedidos y el Display de Cocina (KDS). Delega la lógica de negocio al
# servicio correspondiente (PedidoService) usando inyección de dependencias.
#
# ─── ENDPOINTS ────────────────────────────────────────────────────────────────
#
#   CRUD (requieren auth):
#     GET    /api/v1/pedidos              → listar todos
#     GET    /api/v1/pedidos/{id}         → obtener uno
#     POST   /api/v1/pedidos              → crear (estado inicial: pendiente)
#     PATCH  /api/v1/pedidos/{id}/estado  → avanzar estado (FSM + RBAC)
#
#   KDS:
#     GET    /api/v1/cocina               → sirve el HTML del KDS
#     GET    /api/v1/cocina/pedidos       → pedidos activos de cocina
#
#   WebSocket:
#     WS     /api/v1/cocina/ws            → canal bidireccional autenticado
#
# ─── WEBSOCKET — ARQUITECTURA DE ROOMS ────────────────────────────────────────
#
# El WebSocket usa una arquitectura híbrida de "rooms" (salas):
#
#   ROOMS POR ROL (para el personal):
#     - role:cocina   → cocineros ven todos los pedidos confirmados/preparando
#     - role:pedidos  → cajeros ven todos los cambios de estado
#     - role:admin    → administradores ven todo
#
#   ROOMS POR PEDIDO (para el cliente):
#     - order:{id}    → el cliente solo escucha su propio pedido
#
# ─── FLUJO DEL WEBSOCKET ─────────────────────────────────────────────────────
#
#   1. HANDSHAKE (autenticación):
#      a. Frontend abre WebSocket a ws://host/api/v1/cocina/ws
#      b. El browser envía automáticamente la cookie HttpOnly "access_token"
#      c. El backend extrae el token de la cookie
#      d. Decodifica y valida el JWT (firma + expiración)
#      e. Busca el usuario en BD (existe + activo)
#      f. Si todo es válido, acepta el handshake
#      g. Une el socket a "role:{rol}" via ConnectionManager
#
#   2. ESCUCHA DE MENSAJES:
#      El WebSocket queda en un bucle infinito escuchando mensajes del cliente:
#
#      - subscribe-order: {"action": "subscribe-order", "order_id": 5}
#        → Valida que el pedido pertenece al usuario (solo para role:user)
#        → Une el socket a "order:5"
#        → Responde {"event": "SUBSCRIBED", "data": {"order_id": 5}}
#
#      - unsubscribe-order: {"action": "unsubscribe-order", "order_id": 5}
#        → Remueve el socket de "order:5"
#
#   3. EMISIÓN DE EVENTOS (desde el service):
#      Cuando un pedido cambia de estado, el service emite:
#        a. A la room del pedido:  broadcast_to_order(order_id, event, data)
#        b. A las rooms de rol:    broadcast_to_roles([...], event, data)
#
#   4. DESCONEXIÓN:
#      - Se detecta WebSocketDisconnect
#      - Se remueve el socket de TODAS las rooms via manager.disconnect()
#
# ─── SEGURIDAD ────────────────────────────────────────────────────────────────
#
#   - JWT se lee EXCLUSIVAMENTE de la cookie HttpOnly (no del header Authorization)
#   - HttpOnly + SameSite=lax → protege contra XSS y CSRF
#   - Los clientes solo pueden suscribirse a pedidos propios (validación en BD)
#   - El endpoint FSM requiere roles específicos (cocina/pedidos/admin)
#   - Las rooms son volátiles; al reconectar se debe hacer fetch inicial
#
# ─── CÓDIGOS DE CIERRE WebSocket ─────────────────────────────────────────────
#
#   1000 → Close normal
#   1008 → Policy Violation (token inválido, permisos insuficientes)
#   1001 → Going Away (cliente se desconecta voluntariamente)
#
# =============================================================================

import json
from typing import Annotated
from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlmodel import Session
import pathlib

from app.Core.database import get_session, engine
from app.Core.deps import get_current_active_user, require_role
from app.Core.security import decode_access_token
from app.modules.Usuario.schemas import UsuarioPublic
from app.modules.Usuario.unit_of_work import UsuarioUnitOfWork
from app.modules.Pedido.schemas import PedidoCreate, PedidoPublic, PedidoEstadoUpdate
from app.modules.Pedido.service import PedidoService

# =============================================================================
# CONFIGURACIÓN DEL ROUTER
# =============================================================================

# Router con prefijo /api/v1 — afecta a todas las rutas definidas abajo
router = APIRouter(prefix="/api/v1", tags=["pedidos"])

# Roles autorizados para acceder a los endpoints de cocina/KDS
# Se incluyen variaciones en mayúsculas para robustez en comparación
COCINA_ROLES = ["cocina", "COCINA", "pedidos", "PEDIDOS", "admin", "ADMIN"]

# Roles que pueden gestionar pedidos (para WebSocket y FSM)
# Lista normalizada en minúsculas para lógica interna
STAFF_ROLES = ["admin", "pedidos", "cocina"]


def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    """Factory: inyecta la sesión de BD en el service (dependency injection)."""
    return PedidoService(session)


# =============================================================================
# CRUD DE PEDIDOS (REST API)
# =============================================================================

@router.get("/pedidos", response_model=list[PedidoPublic])
def list_pedidos(
    _user: Annotated[UsuarioPublic, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> list[PedidoPublic]:
    """
    GET /api/v1/pedidos — Lista todos los pedidos del sistema.

    Requiere: cualquier usuario autenticado.
    Retorna: lista completa de pedidos con todos los campos públicos.
    """
    return svc.list_all()


@router.get("/pedidos/mis-pedidos", response_model=list[PedidoPublic])
def list_mis_pedidos(
    current_user: Annotated[UsuarioPublic, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> list[PedidoPublic]:
    """GET /api/v1/pedidos/mis-pedidos — Lista pedidos del usuario autenticado."""
    from app.modules.Pedido.unit_of_work import PedidoUnitOfWork
    with PedidoUnitOfWork(svc._session) as uow:
        pedidos = uow.pedidos.get_by_usuario(current_user.id)
        pedidos.sort(key=lambda p: p.id or 0, reverse=True)
        return [PedidoPublic.model_validate(p) for p in pedidos]


@router.get("/pedidos/{pedido_id}", response_model=PedidoPublic)
def get_pedido(
    pedido_id: int,
    _user: Annotated[UsuarioPublic, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoPublic:
    """
    GET /api/v1/pedidos/{id} — Obtiene un pedido por su ID.

    Requiere: cualquier usuario autenticado.
    Retorna: el pedido completo o 404 si no existe.
    """
    return svc.get_by_id(pedido_id)


@router.post("/pedidos", response_model=PedidoPublic, status_code=status.HTTP_201_CREATED)
async def create_pedido(
    data: PedidoCreate,
    current_user: Annotated[UsuarioPublic, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoPublic:
    return await svc.create(data, usuario_id=current_user.id)


# =============================================================================
# ENDPOINTS DEL DISPLAY DE COCINA (KDS)
# =============================================================================

@router.get("/cocina", response_class=HTMLResponse, tags=["kds"])
def get_cocina_dashboard():
    """
    GET /api/v1/cocina — Sirve la interfaz visual del KDS como HTML.

    Lee el archivo kds.html desde el directorio de templates.
    No requiere autenticación (el login está en el propio HTML).
    """
    html_path = pathlib.Path(__file__).parent.parent.parent / "templates" / "kds.html"
    if not html_path.exists():
        return HTMLResponse("<h2>KDS template not found</h2>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.get("/cocina/pedidos", response_model=list[PedidoPublic])
def list_cocina_pedidos(
    _user: Annotated[UsuarioPublic, Depends(require_role(COCINA_ROLES))],
    svc: PedidoService = Depends(get_pedido_service),
) -> list[PedidoPublic]:
    """
    GET /api/v1/cocina/pedidos — Lista pedidos activos para la pantalla de cocina.

    Requiere: roles cocina, pedidos o admin.
    Filtra solo estados activos de cocina: "confirmado" o "preparando".
    Ordenados por antigüedad (ID ascendente).
    """
    return svc.list_cocina_pedidos()


# =============================================================================
# ENDPOINTS DE SERVICIO PARA FRONTENDS
# =============================================================================

CAJERO_ROLES = ["admin", "pedidos"]


@router.get("/cajero", response_class=HTMLResponse, tags=["cajero"])
def get_cajero_dashboard():
    """GET /api/v1/cajero — Sirve la pantalla del Cajero."""
    html_path = pathlib.Path(__file__).parent.parent.parent / "templates" / "cajero.html"
    if not html_path.exists():
        return HTMLResponse("<h2>Cajero template not found</h2>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.get("/cliente", response_class=HTMLResponse, tags=["cliente"])
def get_cliente_dashboard():
    """GET /api/v1/cliente — Sirve la pantalla del Cliente."""
    html_path = pathlib.Path(__file__).parent.parent.parent / "templates" / "cliente.html"
    if not html_path.exists():
        return HTMLResponse("<h2>Cliente template not found</h2>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.get("/cajero/pedidos", response_model=list[PedidoPublic])
def list_cajero_pedidos(
    _user: Annotated[UsuarioPublic, Depends(require_role(CAJERO_ROLES))],
    svc: PedidoService = Depends(get_pedido_service),
) -> list[PedidoPublic]:
    """GET /api/v1/cajero/pedidos — Lista todos los pedidos para el cajero."""
    return svc.list_all()


@router.get("/cliente/mis-pedidos", response_model=list[PedidoPublic])
def list_cliente_pedidos(
    current_user: Annotated[UsuarioPublic, Depends(get_current_active_user)],
    svc: PedidoService = Depends(get_pedido_service),
) -> list[PedidoPublic]:
    """GET /api/v1/cliente/mis-pedidos — Lista pedidos del usuario autenticado."""
    from app.modules.Pedido.unit_of_work import PedidoUnitOfWork
    with PedidoUnitOfWork(svc._session) as uow:
        pedidos = uow.pedidos.get_all()
        mis = [p for p in pedidos if p.usuario_id == current_user.id]
        mis.sort(key=lambda p: p.id or 0, reverse=True)
        return [PedidoPublic.model_validate(p) for p in mis]


# =============================================================================
# CAMBIO DE ESTADO (FSM — Finite State Machine)
# =============================================================================

@router.patch("/pedidos/{pedido_id}/estado", response_model=PedidoPublic)
async def avanzar_pedido_estado(
    pedido_id: int,
    data: PedidoEstadoUpdate,
    current_user: Annotated[UsuarioPublic, Depends(require_role(COCINA_ROLES))],
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoPublic:
    """
    PATCH /api/v1/pedidos/{id}/estado — Avanza el estado de un pedido (FSM).

    Requiere: roles cocina, pedidos o admin.
    Valida la transición según la FSM + RBAC en un solo lookup.
    Emite eventos WebSocket a rooms relevantes después de persistir.

    Ejemplo de body:
        {"nuevo_estado": "confirmado", "motivo": "Pago verificado"}
    """
    return await svc.avanzar_estado(pedido_id, data.nuevo_estado, current_user)


# =============================================================================
# WEBSOCKET — CANAL BIDIRECCIONAL PARA TIEMPO REAL
# =============================================================================
#
# Este es el endpoint WebSocket principal del sistema.
#
# ─── PROTOCOLO ────────────────────────────────────────────────────────────────
#
# El protocolo sobre WebSocket es JSON bidireccional:
#
#   Cliente → Backend (acciones):
#     {"action": "subscribe-order",   "order_id": 5}
#     {"action": "unsubscribe-order", "order_id": 5}
#
#   Backend → Cliente (eventos):
#     {"event": "PEDIDO_CONFIRMADO",     "data": {...}}
#     {"event": "PEDIDO_EN_PREPARACION", "data": {...}}
#     {"event": "PEDIDO_EN_CAMINO",      "data": {...}}
#     {"event": "PEDIDO_CANCELADO",      "data": {...}}
#     {"event": "PEDIDO_ENTREGADO",      "data": {...}}
#     {"event": "SUBSCRIBED",            "data": {"order_id": 5}}
#     {"event": "ERROR",                 "data": {"detail": "..."}}
#
# ─── AUTENTICACIÓN ────────────────────────────────────────────────────────────
#
# El WebSocket NO soporta headers personalizados en el handshake desde el
# navegador (limitación del API WebSocket del browser). Por eso usamos
# cookies HttpOnly, que se envían automáticamente en el handshake:
#
#   1. El frontend primero hace login via REST: POST /api/v1/auth/token
#   2. El backend setea una cookie HttpOnly con el JWT
#   3. Al abrir el WebSocket, el browser envía la cookie automáticamente
#   4. El backend lee el JWT de la cookie y lo valida
#
# ─── SEGURIDAD ────────────────────────────────────────────────────────────────
#
#   - Solo usuarios activos pueden conectarse
#   - Los clientes (role:user) solo pueden suscribirse a pedidos propios
#   - La validación de propiedad se hace contra la BD (no confía en el cliente)
#   - Los códigos de cierre 1008 transmiten la razón del rechazo al frontend
#
# =============================================================================

@router.websocket("/cocina/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    WebSocket /api/v1/cocina/ws — Canal bidireccional autenticado para tiempo real.

    Flujo completo:
      1. Handshake: valida JWT desde cookie HttpOnly
      2. Conexión: une el socket a room de su rol
      3. Escucha: procesa suscripciones a pedidos específicos
      4. Desconexión: limpia todas las rooms del socket

    Arquitectura de rooms:
      - role:{rol}   → room del rol (cocina, pedidos, admin, user)
      - order:{id}   → room del pedido (solo para clientes)
    """

    # =========================================================================
    # PASO 1: EXTRAER TOKEN DE LA COOKIE HTTPONLY
    # =========================================================================
    # El browser envía automáticamente las cookies en el handshake WebSocket.
    # La cookie "access_token" contiene el JWT firmado.
    #
    # ¿Por qué cookie y no header?
    #   - El API WebSocket del navegador NO permite configurar headers
    #   - Las cookies HttpOnly no son accesibles desde JavaScript (protección XSS)
    #   - SameSite=lax previene ataques CSRF
    #
    token = websocket.cookies.get("access_token")

    if not token:
        # Sin token → rechazar con código 1008 (Policy Violation)
        # IMPORTANTE: debemos aceptar ANTES de close para que el cliente
        # reciba el código y la razón del rechazo
        await websocket.accept()
        await websocket.close(code=1008, reason="Token de autenticación requerido")
        return

    # =========================================================================
    # PASO 2: DECODIFICAR Y VALIDAR EL JWT
    # =========================================================================
    # decode_access_token() valida:
    #   - La firma HMAC (que no fue manipulado)
    #   - La expiración (exp claim)
    #   - Retorna el payload o None si es inválido
    #
    payload = decode_access_token(token)
    if not payload:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token inválido o expirado")
        return

    # Extraer el "sub" (subject) del token — es el username
    username = payload.get("sub")
    if not username:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token inválido")
        return

    # =========================================================================
    # PASO 3: VALIDAR USUARIO EN BASE DE DATOS
    # =========================================================================
    # Aunque el JWT sea válido, el usuario podría:
    #   - Haber sido eliminado de la BD
    #   - Haber sido desactivado (disabled=True)
    #
    # Siempre validamos contra la BD para tener la información más reciente.
    #
    # NOTA: Cualquier rol autenticado puede conectarse al WebSocket.
    # La diferenciación de roles se hace via rooms:
    #   - role:cocina  → recibe eventos de cocina
    #   - role:pedidos → recibe eventos de pedidos
    #   - role:user    → solo recibe eventos de sus pedidos específicos
    #
    with Session(engine) as db_session:
      with UsuarioUnitOfWork(db_session) as uow:
            user = uow.usuarios.get_by_email(username)
            if not user or not user.activo:
               await websocket.accept()
               await websocket.close(code=1008, reason="Usuario inválido o inactivo")
               return
            # Extraer valores primitivos DENTRO de la sesión antes de que se cierre.
            # Evita DetachedInstanceError al acceder a atributos fuera del bloque.
            user_roles: list[str] = [ur.rol_codigo.upper().strip() for ur in user.usuario_roles]
            user_id: int = user.id  # type: ignore[assignment]

    # =========================================================================
    # PASO 4: REGISTRAR EN EL CONNECTION MANAGER
    # =========================================================================
    from app.Core.websocket import manager
    primary_role = user_roles[0] if user_roles else "user"
    await manager.connect(websocket, role=primary_role, user_id=user_id)

    # Unirse a todas las rooms de rol adicionales (ej: admin que también es cajero)
    from app.Core.websocket import manager as mgr
    for extra_role in user_roles[1:]:
        mgr._join_room(websocket, f"role:{extra_role.lower()}")

    # =========================================================================
    # PASO 5: BUCLE DE ESCUCHA DE MENSAJES
    # =========================================================================
    # El WebSocket queda en un bucle infinito procesando mensajes del cliente.
    #
    # Soporta dos acciones:
    #   - subscribe-order:   suscribirse a actualizaciones de un pedido
    #   - unsubscribe-order: desuscribirse de un pedido
    #
    # El bucle se rompe con WebSocketDisconnect (el cliente cerró la conexión)
    # o con cualquier otro error (se limpia la conexión).
    #
    try:
        while True:
            # Espera bloqueante: receive_text() se rompe cuando el cliente envía
            # un mensaje o cuando se desconecta (lanza WebSocketDisconnect)
            raw = await websocket.receive_text()

            # Parsear el mensaje JSON del cliente
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                # Mensaje malformado → ignorar y seguir escuchando
                continue

            action = msg.get("action")

            # ─── ACCIÓN: SUBSCRIBE-ORDER ──────────────────────────────────────
            # El cliente quiere suscribirse a las actualizaciones de un pedido.
            #
            # Para clientes (role:user):
            #   1. Valida que el pedido exista
            #   2. Valida que el pedido pertenezca al usuario
            #   3. Si es válido, une el socket a "order:{orderId}"
            #
            # Para staff (admin/pedidos/cocina):
            #   Se suscribe directamente (el staff puede ver cualquier pedido)
            #
            if action == "subscribe-order":
                order_id = msg.get("order_id")
                if not order_id or not isinstance(order_id, int):
                    continue

                # Validación de propiedad: solo para clientes (no staff)
                # Los staff pueden ver todos los pedidos
                if not any(r in ("ADMIN", "PEDIDOS", "COCINA") for r in user_roles):
                    with Session(engine) as db_session:
                        with UsuarioUnitOfWork(db_session) as uow:
                            from app.modules.Pedido.unit_of_work import PedidoUnitOfWork
                            pedido_uow = PedidoUnitOfWork(db_session)
                            pedido = pedido_uow.pedidos.get_by_id(order_id)

                            # Validar que:
                            #   a. El pedido exista
                            #   b. El pedido pertenezca al usuario autenticado
                            if not pedido or pedido.usuario_id != user_id:
                                await websocket.send_json({
                                    "event": "ERROR",
                                    "data": {"detail": "No autorizado para este pedido"}
                                })
                                continue

                # Todo válido → unir el socket a la room del pedido
                manager.join_order_room(websocket, order_id)

                # Confirmar al cliente que se suscribió exitosamente
                await websocket.send_json({
                    "event": "SUBSCRIBED",
                    "data": {"order_id": order_id}
                })

            # ─── ACCIÓN: UNSUBSCRIBE-ORDER ────────────────────────────────────
            # El cliente deja de escuchar un pedido específico.
            #
            elif action == "unsubscribe-order":
                order_id = msg.get("order_id")
                if order_id and isinstance(order_id, int):
                    manager.leave_order_room(websocket, order_id)

    except WebSocketDisconnect:
        # El cliente cerró la conexión limpiamente
        manager.disconnect(websocket)
    except Exception:
        # Error inesperado → limpiar la conexión
        manager.disconnect(websocket)
