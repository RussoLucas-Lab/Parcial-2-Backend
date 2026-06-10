# =============================================================================
# SERVICIO DE PEDIDOS — Lógica de Negocio + WebSocket Rooms
# =============================================================================
#
# Este módulo encapsula toda la lógica transaccional de los pedidos y el
# Display de Cocina (KDS). Se comunica con los repositorios a través del
# patrón Unit of Work (UoW) asegurando atomicidad en las operaciones de BD.
#
# ─── RESPONSABILIDADES ────────────────────────────────────────────────────────
#
#   1. CRUD de pedidos (crear, consultar, listar)
#   2. Filtrado de pedidos para KDS (solo estados activos de cocina)
#   3. Gestión de transiciones FSM (Máquina de Estados Finita)
#   4. Validación RBAC (qué roles pueden hacer qué transiciones)
#   5. Emisión de eventos WebSocket a rooms relevantes
#
# ─── ARQUITECTURA DE EMISIÓN WebSocket ────────────────────────────────────────
#
# Cuando un pedido cambia de estado, el service emite eventos a DOS tipos
# de rooms simultáneamente:
#
#   1. ROOM DEL PEDIDO (order:{orderId})
#      - Siempre se notifica
#      - El cliente que hizo el pedido recibe la actualización
#      - Ejemplo: broadcast_to_order(5, "PEDIDO_CONFIRMADO", data)
#
#   2. ROOMS DE ROL (role:{rol})
#      - Se notifican solo los roles relevantes para cada transición
#      - El personal recibe solo lo que le compete
#      - Ejemplo: broadcast_to_roles(["cocina", "pedidos"], event, data)
#
# ─── MAPEO DE TRANSICIONES → ROOMS ────────────────────────────────────────────
#
#   Estado destino    → Roles notificados     → Evento WebSocket
#   ─────────────────────────────────────────────────────────────
#   confirmado        → pedidos, cocina       → PEDIDO_CONFIRMADO
#   preparando        → cocina, pedidos       → PEDIDO_EN_PREPARACION
#   enviado           → pedidos               → PEDIDO_EN_CAMINO
#   entregado         → pedidos               → PEDIDO_ENTREGADO
#   cancelado         → pedidos, cocina       → PEDIDO_CANCELADO
#
# ─── FLUJO COMPLETO DE UNA TRANSICIÓN ────────────────────────────────────────
#
#   1. Frontend llama: PATCH /api/v1/pedidos/{id}/estado
#   2. Router valida RBAC (require_role)
#   3. Service valida FSM + RBAC en un solo lookup
#   4. Service persiste el cambio en BD (dentro de UoW)
#   5. Service emite eventos WebSocket (fuera del UoW):
#      a. broadcast_to_order(order_id, event, data)  → cliente
#      b. broadcast_to_roles(roles, event, data)     → personal
#   6. Retorna el pedido actualizado al frontend REST
#
# =============================================================================

import logging
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.Pedido.model import Pedido
from app.modules.Pedido.schemas import DetallePedidoResponse, PedidoCreate, PedidoPublic
from app.modules.Pedido.unit_of_work import PedidoUnitOfWork
from app.modules.Usuario.schemas import UsuarioPublic

# Logger del módulo para trazabilidad de transiciones y eventos
logger = logging.getLogger("app.modules.Pedido.service")


# =============================================================================
# NORMALIZACIÓN DE ESTADOS
# =============================================================================
#
# Unifica variaciones de entrada (inglés, mayúsculas, abreviaturas) a valores
# canónicos en minúsculas. Esto permite que el frontend envíe "Pendiente",
# "pending" o "PENDIENTE" y siempre se resuelva a "pendiente".
#
# Ejemplo de uso:
#   estado_db = "PENDIENTE"
#   estado_normalizado = ESTADOS.get(estado_db, estado_db)  # → "pendiente"
#
ESTADOS = {
    # Valores canónicos de la BD (pass-through)
    "PENDIENTE":  "PENDIENTE",
    "CONFIRMADO": "CONFIRMADO",
    "EN_PREP":    "EN_PREP",
    "ENTREGADO":  "ENTREGADO",
    "CANCELADO":  "CANCELADO",
    # Español minúsculas / aliases
    "pendiente":      "PENDIENTE",
    "confirmado":     "CONFIRMADO",
    "preparando":     "EN_PREP",
    "en_preparacion": "EN_PREP",
    "en_prep":        "EN_PREP",
    "entregado":      "ENTREGADO",
    "cancelado":      "CANCELADO",
    # Inglés
    "pending":   "PENDIENTE",
    "confirmed": "CONFIRMADO",
    "delivered": "ENTREGADO",
    "cancelled": "CANCELADO",
}


# =============================================================================
# FSM + PERMISOS POR ROL (TRANSICIONES)
# =============================================================================
#
# Diccionario unificado que define:
#   - Qué transiciones puede hacer cada rol (RBAC)
#   - Qué transiciones son válidas según el estado actual (FSM)
#
# Estructura: TRANSICIONES[ROL][ESTADO_ACTUAL] = {estados_destino_posibles}
#
# Si un rol no está en el dict → no tiene permisos para avanzar estados.
# Si un estado no está en las keys del rol → no admite transiciones desde ahí.
#
# Ejemplo de lookup:
#   rol = "COCINA"
#   origen = "confirmado"
#   permitidos = TRANSICIONES.get("COCINA", {}).get("confirmado", set())
#   # → {"preparando"}
#   if "preparando" not in permitidos:
#       raise HTTPException(403, "Transición no permitida")
#
TRANSICIONES = {
    # Admin puede hacer CUALQUIER transición válida
    "ADMIN": {
        "PENDIENTE":  {"CONFIRMADO", "CANCELADO"},
        "CONFIRMADO": {"EN_PREP",    "CANCELADO"},
        "EN_PREP":    {"ENTREGADO",      "CANCELADO"},
        "ENTREGADO":  set(),
        "CANCELADO":  set(),
    },
    # Cajero: confirma, cancela pedidos
    "PEDIDOS": {
        "PENDIENTE":  {"CONFIRMADO", "CANCELADO"},
        "CONFIRMADO": {"CANCELADO"},
        "EN_PREP":    {"CANCELADO"},
        "ENTREGADO":  set(),
        "CANCELADO":  set(),
    },
    # Cocina: prepara y entrega directamente
    "COCINA": {
        "CONFIRMADO": {"EN_PREP"},
        "EN_PREP":    {"ENTREGADO"},
    },
}


# =============================================================================
# EVENTOS WebSocket
# =============================================================================
#
# Mapea cada estado destino al nombre del evento WebSocket que se envía
# al frontend. Los nombres siguen convención SCREAMING_SNAKE_CASE.
#
# Estos eventos son los que el frontend KDS escucha en socket.onmessage.
#
EVENTOS_WS = {
    "PENDIENTE":  "NUEVO_PEDIDO",
    "CONFIRMADO": "PEDIDO_CONFIRMADO",
    "EN_PREP":    "PEDIDO_EN_PREPARACION",
    "CANCELADO":  "PEDIDO_CANCELADO",
    "ENTREGADO":  "PEDIDO_ENTREGADO",
}


# =============================================================================
# ROLES POR TRANSICIÓN (para emisión WebSocket)
# =============================================================================
#
# Define qué roles de staff deben ser notificados cuando un pedido llega
# a cada estado. La room del pedido (order:{orderId}) SIEMPRE se notifica,
# esto es solo para las rooms de rol.
#
# Lógica de negocio detrás de cada regla:
#   - confirmado → pedidos + cocina
#     El cajero confirmó el pago, la cocina debe saber que hay un nuevo pedido
#
#   - preparando → cocina + pedidos
#     La cocina inició la preparación, pedidos monitorea el progreso
#
#   - entregado → pedidos + cocina
#     La cocina entregó el pedido directamente
#
#   - cancelado → pedidos + cocina
#     Todos los involucrados deben saber que se canceló
#
ROLES_POR_TRANSICION = {
    "PENDIENTE":  ["pedidos", "admin"],
    "CONFIRMADO": ["pedidos", "cocina", "admin"],
    "EN_PREP":    ["cocina", "pedidos", "admin"],
    "ENTREGADO":  ["pedidos", "cocina", "admin"],
    "CANCELADO":  ["pedidos", "cocina", "admin"],
}


# =============================================================================
# CLASE DE SERVICIO
# =============================================================================

class PedidoService:
    """
    Servicio de Pedidos — lógica de negocio del módulo.

    Responsabilidades:
      - CRUD de pedidos (crear, consultar, listar)
      - Filtrado de pedidos para KDS
      - Gestión de transiciones FSM + RBAC
      - Emisión de eventos WebSocket a rooms relevantes

    Patrón:
      - Recibe la sesión de BD via dependency injection (FastAPI)
      - Usa Unit of Work para operaciones transaccionales
      - Delega al ConnectionManager para eventos WebSocket
    """

    def __init__(self, session: Session) -> None:
        """
        Inicializa el servicio con una sesión de BD.

        La sesión es inyectada por FastAPI vía Depends(get_session).
        Se usa para crear el Unit of Work en cada operación.
        """
        self._session = session

    # =========================================================================
    # OPERACIONES CRUD
    # =========================================================================

    def list_all(self) -> list[PedidoPublic]:
        """
        Lista todos los pedidos del sistema.

        Retorna:
            Lista de pedidos serializados como PedidoPublic.
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedidos = uow.pedidos.get_all()
            result = [PedidoPublic.model_validate(p) for p in pedidos]
        return result

    def get_by_id(self, pedido_id: int) -> PedidoPublic:
        """
        Busca un pedido por su ID.

        Raises:
            HTTPException 404: si el pedido no existe.
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )
            result = PedidoPublic.model_validate(pedido)
        return result

    async def create(self, data: PedidoCreate, usuario_id: int) -> PedidoPublic:
        """
        Crea un nuevo pedido y notifica al cajero vía WebSocket.
        """
        from decimal import Decimal
        from app.modules.DetallePedido.model import DetallePedido

        with PedidoUnitOfWork(self._session) as uow:
            # Resolver productos y calcular subtotal
            subtotal = Decimal("0.00")
            detalles_data = []
            for item in data.detalles:
                producto = uow.productos.get_by_id(item.producto_id)
                if not producto:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto {item.producto_id} no encontrado",
                    )
                precio = producto.precio_base
                sub = precio * item.cantidad
                subtotal += sub
                detalles_data.append((item, producto.nombre, precio, sub))

            costo_envio = Decimal("50.00") if data.direccion_id else Decimal("0.00")
            total = subtotal + costo_envio

            pedido = Pedido(
                usuario_id=usuario_id,
                direccion_id=data.direccion_id,
                forma_pago_codigo=data.forma_pago_codigo,
                estado_codigo="PENDIENTE",
                notas=data.notas,
                subtotal=subtotal,
                descuento=Decimal("0.00"),
                costo_envio=costo_envio,
                total=total,
            )
            uow.pedidos.add(pedido)
            uow.session.flush()  # obtener pedido.id antes de crear detalles

            for item, nombre, precio, sub in detalles_data:
                detalle = DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    nombre_snapshot=nombre,
                    precio_snapshot=precio,
                    subtotal_snap=sub,
                    personalizacion=item.personalizacion,
                )
                uow.session.add(detalle)

            uow.session.flush()

            result = PedidoPublic(
                id=pedido.id,
                usuario_id=pedido.usuario_id,
                direccion_id=pedido.direccion_id,
                estado_codigo=pedido.estado_codigo,
                forma_pago_codigo=pedido.forma_pago_codigo,
                subtotal=pedido.subtotal,
                descuento=pedido.descuento,
                costo_envio=pedido.costo_envio,
                total=pedido.total,
                notas=pedido.notas,
                detalles=[
                    DetallePedidoResponse(
                        producto_id=item.producto_id,
                        cantidad=item.cantidad,
                        nombre_snapshot=nombre,
                        precio_snapshot=precio,
                        subtotal_snap=sub,
                    )
                    for item, nombre, precio, sub in detalles_data
                ],
            )

        # Notificar al cajero que llegó un pedido nuevo
        await self._emit_ws_events(result.id, "PENDIENTE", result)
        return result

    def list_cocina_pedidos(self) -> list[PedidoPublic]:
        """
        Obtiene la lista de pedidos activos para la pantalla de cocina (KDS).

        Reglas de negocio:
          - Solo estados activos de cocina: "confirmado" o "preparando"
          - Ordenados por antigüedad (ID ascendente) — primero los más viejos

        Este endpoint se usa tanto para el carga inicial del KDS (REST)
        como para el polling de respaldo cuando se cae el WebSocket.
        """
        with PedidoUnitOfWork(self._session) as uow:
            all_pedidos = uow.pedidos.get_all()
            cocina_pedidos = [
                p for p in all_pedidos
                if p.estado_codigo in ("CONFIRMADO", "EN_PREP")
            ]
            cocina_pedidos.sort(key=lambda p: p.id or 0)
            result = [PedidoPublic.model_validate(p) for p in cocina_pedidos]
        return result

    # =========================================================================
    # TRANSICIÓN DE ESTADO (FSM + RBAC + WebSocket)
    # =========================================================================

    async def avanzar_estado(
        self, pedido_id: int, nuevo_estado: str, current_user: UsuarioPublic
    ) -> PedidoPublic:
        """
        Avanza el estado de un pedido aplicando FSM + RBAC en un solo lookup.

        Este es el método MÁS IMPORTANTE del servicio — orquesta:
          1. Validación de existencia del pedido
          2. Normalización de estados (inglés/español/abreviaturas)
          3. Validación FSM + RBAC en un solo lookup O(1)
          4. Persistencia del cambio en BD (dentro de UoW)
          5. Auditoría en logs
          6. Emisión de eventos WebSocket a rooms relevantes

        Args:
            pedido_id:    ID del pedido a actualizar
            nuevo_estado: Estado destino (se normaliza vía dict ESTADOS)
            current_user: Usuario autenticado que realiza la transición

        Raises:
            HTTPException 404: si el pedido no existe
            HTTPException 403: si la transición no está permitida para el rol

        Returns:
            PedidoPublic con el estado actualizado
        """

        with PedidoUnitOfWork(self._session) as uow:
            # ─── PASO 1: Buscar el pedido ─────────────────────────────────────
            pedido = uow.pedidos.get_by_id(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )

            # ─── PASO 2: Normalizar estados ───────────────────────────────────
            # Convierte variaciones a valores canónicos en minúsculas
            # Ejemplo: "PENDIENTE" → "pendiente", "en_prep" → "preparando"
            origen = ESTADOS.get(pedido.estado_codigo, pedido.estado_codigo)
            destino = ESTADOS.get(nuevo_estado, nuevo_estado)

            # Si el origen y destino son iguales, no hay nada que hacer
            if origen == destino:
               return PedidoPublic.model_validate(pedido) # Para actualizar la fecha de modificación
            
            # ─── PASO 3: Validar FSM + RBAC en un solo lookup ────────────────
            # Este es el corazón de la validación:
            #   TRANSICIONES[ROL][ESTADO_ORIGEN] → {estados_destino_permitidos}
            #
            # Si el rol no está en el dict → set() vacío → 403
            # Si el estado no está en las keys del rol → set() vacío → 403
            # Si el destino no está en el set → 403
            #
            # Complejidad: O(1) — un solo lookup en dict anidado
            #
            roles_usuario = [r.upper().strip() for r in current_user.roles]
            permitidos = set()
            for rol in roles_usuario:
               permitidos |= TRANSICIONES.get(rol, {}).get(origen, set())

            if destino not in permitidos:
               raise HTTPException(
                  status_code=status.HTTP_403_FORBIDDEN,
                  detail=f"Transición no permitida para tu rol: '{pedido.estado}' → '{nuevo_estado}'",
               )

            # ─── PASO 4: Auditoría ────────────────────────────────────────────
            # Log detallado para trazabilidad y cumplimiento
            logger.info(
               f"AUDITORÍA FSM: Usuario {current_user.nombre} "
               f"(ID: {current_user.id}, Rol: {current_user.roles}) "
               f"avanzó pedido {pedido_id} de '{pedido.estado}' a '{nuevo_estado}'"
            )

            # ─── PASO 5: Persistir el cambio ──────────────────────────────────
            pedido.estado_codigo = destino
            uow.pedidos.update(pedido)
            result = PedidoPublic.model_validate(pedido)

        # ─── PASO 6: Emitir eventos WebSocket (FUERA del bloque transaccional) ─
        # Se emite después del commit del UoW para asegurar que los datos
        # estén persistidos antes de notificar a los clientes.
        await self._emit_ws_events(pedido_id, destino, result)

        return result

    # =========================================================================
    # EMISIÓN DE EVENTOS WebSocket
    # =========================================================================

    async def _emit_ws_events(
        self, pedido_id: int, destino: str, result: PedidoPublic
    ) -> None:
        """
        Emite eventos WebSocket a las rooms relevantes según el estado destino.

        Este método implementa la lógica de notificación selectiva:
          1. SIEMPRE emite a la room del pedido (order:{orderId})
             → El cliente que hizo el pedido recibe la actualización
          2. Emite a las rooms de los roles relevantes
             → El personal recibe solo lo que le compete

        El evento incluye el pedido completo serializado como diccionario,
        para que el frontend pueda actualizar su estado local sin hacer
        un fetch adicional a la API REST.

        Args:
            pedido_id: ID del pedido (para la room order:{id})
            destino:   Estado al que se transitionó (para mapear el evento)
            result:    PedidoPublic con los datos actualizados
        """
        from app.Core.websocket import manager

        # Mapear estado destino → nombre del evento WebSocket
        # Si el estado no tiene evento asociado (ej: "pendiente"), no se emite
        event_type = EVENTOS_WS.get(destino)
        if not event_type:
            return

        # Serializar el pedido a diccionario para enviar como JSON
        # mode="json" convierte Decimal → float para que sea JSON-serializable
        data = result.model_dump(mode="json")

        # ─── NOTIFICAR AL CLIENTE (room del pedido) ──────────────────────────
        # El cliente que hizo el pedido siempre recibe la actualización,
        # sin importar qué rol procesó el cambio.
        #
        # Ejemplo: si el pedido #5 pasó a "confirmado":
        #   broadcast_to_order(5, "PEDIDO_CONFIRMADO", pedido_data)
        #   → El socket del cliente en "order:5" recibe el evento
        #
        await manager.broadcast_to_order(pedido_id, event_type, data)

        # ─── NOTIFICAR A LOS ROLES RELEVANTES ───────────────────────────────
        # Cada transición notifica a los roles que necesitan saber el cambio.
        # La configuración está en ROLES_POR_TRANSICION.
        #
        # Ejemplo: si el pedido pasó a "confirmado":
        #   broadcast_to_roles(["pedidos", "cocina"], "PEDIDO_CONFIRMADO", data)
        #   → Los sockets en "role:pedidos" y "role:cocina" reciben el evento
        #   → Un socket que esté en ambas rooms solo recibe una vez (deduplicación)
        #
        roles_a_notificar = ROLES_POR_TRANSICION.get(destino, [])
        if roles_a_notificar:
            await manager.broadcast_to_roles(roles_a_notificar, event_type, data)

        logger.info(
            f"WS emitido: {event_type} | pedido={pedido_id} | "
            f"roles={roles_a_notificar} | rooms_activas={manager.get_rooms_info()}"
        )
