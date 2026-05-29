from fastapi import APIRouter, WebSocket
from sqlmodel import Session
from app.Core.database import get_session, engine
from app.Core.auth import decode_access_token
from fastapi.websockets import WebSocketDisconnect
from app.Core.websocket import manager
from app.modules.Usuario.unit_of_work import UsuarioUnitOfWork


router = APIRouter(prefix="/api/v1/", tags=["Cocina"],)

# ─── WebSocket para tiempo real ─────────────────────────────────────────────
@router.websocket("/cocina/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    # WebSocket /api/v1/cocina/ws — canal bidireccional para el KDS.
    #
    # Flujo de seguridad en el handshake:
    #   1. Obtiene token JWT desde cookie HttpOnly "access_token"
    #   2. Decodifica y valida firma + expiración
    #   3. Verifica en BD que el usuario exista, esté activo y tenga rol cocina/admin
    #   4. Registra en ConnectionManager para recibir broadcasts
    #   5. Mantiene conexión abierta escuchando desconexiones

    # 1. Obtener el token de la cookie HttpOnly
    token = websocket.cookies.get("access_token")

    if not token:
        # WebSocket requiere accept() antes de close() para poder enviar
        # el código 1008 (Policy Violation) con la razón al cliente.
        # Sin accept(), el navegador ve "Connection closed" genérico.
        await websocket.accept()
        await websocket.close(code=1008, reason="Token de autenticación requerido")
        return

    # 2. Decodificar y validar el JWT
    payload = decode_access_token(token)
    if not payload:
        # accept + close(code=1008): mismo patrón — completar handshake
        # para transmitir la razón del rechazo al cliente WebSocket
        await websocket.accept()
        await websocket.close(code=1008, reason="Token inválido o expirado")
        return

    username = payload.get("sub")
    if not username:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token inválido")
        return

    # 3. Validar usuario y rol en BD
    with Session(engine) as db_session:
        with UsuarioUnitOfWork(db_session) as uow:
            user = uow.usuarios.get_by_username(username)
            if not user or user.disabled:
                # Misma mecánica: accept() obligatorio antes de close()
                # para que event.code y event.reason lleguen al frontend
                await websocket.accept()
                await websocket.close(code=1008, reason="Usuario inválido o inactivo")
                return

            # Compara rol ignorando mayúsculas y espacios
            rol_upper = user.role.upper().strip()
            if rol_upper not in ("COCINA", "PEDIDOS", "ADMIN"):
                await websocket.accept()
                await websocket.close(code=1008, reason="Permisos insuficientes")
                return

    # 4. Registrar en el ConnectionManager global
    await manager.connect(websocket)

    try:
        # 5. Bucle infinito: espera mensajes (detecta desconexiones)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
