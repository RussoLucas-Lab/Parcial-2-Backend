from sqlmodel import Session, select

from app.Core.security import hash_password
from app.modules.EstadoPedido.model import EstadoPedido

from app.Core.database import engine, create_db_and_tables

from app.modules.Rol.model import Rol
from app.modules.FormaPago.model import FormaPago
from app.modules.Usuario.model import Usuario, UsuarioRol

# ── Roles ───────────────────────────────────────────────────────────
ROLES = [
   Rol(
      codigo="ADMIN",
      nombre="Administrador",
      descripcion="Acceso total sin restricciones",
   ),
   Rol(
      codigo="CAJERO",
      nombre="Cajero",
      descripcion="Gestiona ventas y caja",
   ),
   Rol(
      codigo="COCINA",
      nombre="Cocina",
      descripcion="Prepara pedidos y actualiza estados",
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

USUARIOS_INICIALES = [
    {
        "nombre": "Admin",
        "apellido": "Sistema",
        "email": "admin@example.com",
        "celular": "2610000000",
        "password": "Admin1234!",
        "roles": ["ADMIN"],
    },
    {
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan@example.com",
        "celular": "2611111111",
        "password": "Juan1234!",
        "roles": ["CLIENT"],
        
    },
    {
        "nombre": "Carlos",
        "apellido": "Sanchez",
        "email": "carlos@example.com",
        "celular": "2612222222",
        "password": "Carlos1234!",
        "roles": ["PEDIDOS"],
        
    },
    {
        "nombre": "Pablo",
        "apellido": "Garcia",
        "email": "pablo@example.com",
        "celular": "2613333333",
        "password": "Pablo1234!",
        "roles": ["STOCK"],
        
    },

]


def seed_usuarios(session: Session) -> None:
    print("=== Seed — Usuarios Iniciales ===")

    create_db_and_tables()

    with Session(engine) as session:

        for data in USUARIOS_INICIALES:

            existing = session.exec(
                select(Usuario).where(
                    Usuario.email == data["email"]
                )
            ).first()

            if existing:
                print(f"[=] Ya existe: {data['email']}")
                continue

            usuario = Usuario(
                nombre=data["nombre"],
                apellido=data["apellido"],
                email=data["email"],
                celular=data["celular"],
                password_hash=hash_password(data["password"]),
            )

            session.add(usuario)

            # Necesario para obtener usuario.id
            session.flush()

            # Asignar roles
            for rol_codigo in data["roles"]:

                rol = session.get(Rol, rol_codigo)

                if not rol:
                    print(f"[!] Rol inexistente: {rol_codigo}")
                    continue

                usuario_rol = UsuarioRol(
                    usuario_id=usuario.id,
                    rol_codigo=rol_codigo,
                )

                session.add(usuario_rol)

            print(
                f"[+] Creado: {usuario.email} "
                f"(roles={data['roles']})"
            )

        session.commit()