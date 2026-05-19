from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.deps import get_current_user, require_role

from app.modules.Pedido.schemas import PedidoCreate, PedidoResponse
from app.modules.Pedido.service import PedidoService
from app.modules.Usuario.model import Usuario


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)

# ─────────────────────────────────────────────
# CLIENT: crear pedido
# ─────────────────────────────────────────────

@router.post(
    "",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["CLIENT"]))]
)
def create_pedido(
    data: PedidoCreate,
    current_user: Usuario = Depends(get_current_user),
    service: PedidoService = Depends(get_pedido_service)
):
    return service.create(data, current_user.id)


# ─────────────────────────────────────────────
# CLIENT: ver mis pedidos
# ─────────────────────────────────────────────

@router.get(
    "/mis-pedidos",
    response_model=list[PedidoResponse],
    dependencies=[Depends(require_role(["CLIENT"]))]
)
def get_mis_pedidos(
    current_user: Usuario = Depends(get_current_user),
    service: PedidoService = Depends(get_pedido_service)
):
    return service.get_by_usuario(current_user.id)


# ─────────────────────────────────────────────
# CLIENT: ver pedido por ID
# ─────────────────────────────────────────────

@router.get(
    "/{pedido_id}",
    response_model=PedidoResponse,
    dependencies=[Depends(require_role(["CLIENT"]))]
)
def get_pedido_by_id(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    service: PedidoService = Depends(get_pedido_service)
):
    pedido = service.get_by_id(pedido_id)

    if pedido.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    return pedido


# ─────────────────────────────────────────────
# PEDIDOS / ADMIN: cambiar estado
# ─────────────────────────────────────────────

@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoResponse,
    dependencies=[Depends(require_role(["PEDIDOS", "ADMIN"]))]
)
def cambiar_estado(
    pedido_id: int,
    nuevo_estado: str,
    current_user: Usuario = Depends(get_current_user),
    service: PedidoService = Depends(get_pedido_service)
):
    return service.cambiar_estado(
        pedido_id=pedido_id,
        nuevo_estado=nuevo_estado,
        usuario_id=current_user.id
    )


# ─────────────────────────────────────────────
# CLIENT: cancelar pedido
# ─────────────────────────────────────────────

@router.patch(
    "/{pedido_id}/cancelar",
    response_model=PedidoResponse,
    dependencies=[Depends(require_role(["CLIENT"]))]
)
def cancelar_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    service: PedidoService = Depends(get_pedido_service)
):
    pedido = service.get_by_id(pedido_id)

    if pedido.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    return service.cambiar_estado(
        pedido_id=pedido_id,
        nuevo_estado="CANCELADO",
        usuario_id=current_user.id
    )