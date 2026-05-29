# Gestor de conexiones WebSocket para el Kitchen Display System (KDS).
#
# Mantiene un registro de las pantallas de cocina conectadas y permite
# difundir eventos en tiempo real cuando cambia el estado de un pedido.
#
# Eventos emitidos:
#   PEDIDO_CONFIRMADO    → nuevo pedido listo para cocinar
#   PEDIDO_EN_PREPARACION → pedido siendo cocinado
#   PEDIDO_EN_CAMINO     → pedido despachado a delivery
#   PEDIDO_ENTREGADO     → pedido entregado al cliente
#
# Arquitectura:
#   - manager (singleton global) → se importa desde service.py para hacer broadcast
#   - Cada pantalla KDS abre una conexión → se registra en active_connections
#   - El ciclo de vida lo maneja el router de pedidos (websocket_endpoint)

import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("app.core.websocket")


class ConnectionManager:
   # Gestor de conexiones WebSocket

   def __init__(self) -> None:
      # Set de conexiones activas. Se usa set para evitar duplicados.
      self.active_connections: set[WebSocket] = set()

   async def connect(self, websocket: WebSocket) -> None:
      # Acepta el handshake y registra la conexión
      await websocket.accept()
      self.active_connections.add(websocket)
      logger.info(
            f"Nueva conexión KDS. Total activas: {len(self.active_connections)}"
      )

   def disconnect(self, websocket: WebSocket) -> None:
      # Elimina la conexión del registro. discard no lanza error si no existe.
      self.active_connections.discard(websocket)
      logger.info(
            f"Conexión KDS finalizada. Total activas: {len(self.active_connections)}"
      )

   async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
      # Envía un evento JSON a todas las pantallas KDS conectadas.
      # Si una conexión falla, la remueve y continúa con las demás.
      payload = {"event": event_type, "data": data}
      if not self.active_connections:
            logger.info(f"Evento {event_type} descartado (sin pantallas conectadas).")
            return

      logger.info(
            f"Broadcast {event_type} a {len(self.active_connections)} conexiones."
      )
      for connection in list(self.active_connections):
            try:
               await connection.send_json(payload)
            except Exception as e:
               # Conexión caída — la removemos y seguimos
               logger.warning(f"Error al enviar WebSocket. Removiendo conexión: {e}")
               self.active_connections.discard(connection)


# Instancia global (singleton) del gestor de conexiones
# Se importa desde service.py (PedidoService.avanzar_estado) y desde router.py
manager = ConnectionManager()
