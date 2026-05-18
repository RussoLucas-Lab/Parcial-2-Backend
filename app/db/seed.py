from sqlmodel import Session

from app.modules.EstadoPedido.model import EstadoPedido
from app.modules.Rol.model import Rol
from app.modules.FormaPago.model import FormaPago

# ── Roles ───────────────────────────────────────────────────────────
ROLES = [
   Rol(
      codigo="ADMIN",
      nombre="Administrador",
      descripcion="Acceso total sin restricciones",
   ),
   Rol(
      codigo="STOCK",
      nombre="Stock",
      descripcion="Actualiza stock y disponible",
   ),
   Rol(
      codigo="PEDIDOS",
      nombre="Pedidos",
      descripcion="Avanza estados CONFIRMADO→ENTREGADO",
   ),
   Rol(
      codigo="CLIENT",
      nombre="Cliente",
      descripcion="Opera solo sus propios datos",
   ),
]

def seed_roles(session: Session) -> None:

   for rol in ROLES:

      exists = session.get(Rol, rol.codigo)

      if not exists:
            session.add(rol)

   session.commit()

# ── Formas de Pago ───────────────────────────────────────────────────────

FORMAS_PAGO = [ 
   FormaPago(
      codigo="EFECTIVO",
      nombre="Efectivo",
      descripcion="Pago en efectivo al recibir el pedido"
   ), 
   FormaPago(
      codigo="TARJETA",
      nombre="Tarjeta de Crédito",
      descripcion="Pago con tarjeta de crédito"
   ),
   FormaPago(
      codigo="TRANSFERENCIA",
      nombre="Transferencia Bancaria",
      descripcion="Pago mediante transferencia bancaria"
   ),
]

def seed_formas_pago(session: Session) -> None:

   for forma_pago in FORMAS_PAGO:

      exists = session.get(FormaPago, forma_pago.codigo)

      if not exists:
            session.add(forma_pago)

   session.commit()

# ── Estados de Pedido ────────────────────────────────────────────────
ESTADOS_PEDIDO = [
   EstadoPedido(
      codigo="PENDIENTE",
      descripcion="Pedido pendiente",
      orden=1,
      es_terminal=False
   ),
   EstadoPedido(
      codigo="CONFIRMADO",
      descripcion="Pedido confirmado",
      orden=2,
      es_terminal=False
   ),
   EstadoPedido(
      codigo="EN_PREP",
      descripcion="Pedido en preparación",
      orden=3,
      es_terminal=False
   ),
   EstadoPedido(
      codigo="EN_CAMINO",
      descripcion="Pedido en camino",
      orden=4,
      es_terminal=False
   ),
   EstadoPedido(
      codigo="ENTREGADO",
      descripcion="Pedido entregado",
      orden=5,
      es_terminal=True
   ),
   EstadoPedido(
      codigo="CANCELADO",
      descripcion="Pedido cancelado",
      orden=6,
      es_terminal=True
   ),
]

def seed_estados_pedido(session):
   for estado in ESTADOS_PEDIDO:
      existe = session.get(EstadoPedido, estado.codigo)

      if not existe:
            session.add(estado)

   session.commit()