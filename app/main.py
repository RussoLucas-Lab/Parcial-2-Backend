from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlmodel import SQLModel, Session

from app.Core.database import engine


# =========================================
# IMPORTS DE TODOS LOS MODELOS
# =========================================

from app.modules.Categoria.model import Categoria
from app.modules.Ingrediente.model import Ingrediente

from app.modules.Producto.model import (
   Producto,
   ProductoIngrediente,
   ProductoCategoria
)

from app.modules.Usuario.model import Usuario
from app.modules.Rol.model import Rol
from app.modules.Auth.model import RefreshToken
from app.modules.DireccionEntrega.model import DireccionEntrega
from app.modules.Pedido.model import Pedido
from app.modules.DetallePedido.model import DetallePedido
from app.modules.EstadoPedido.model import EstadoPedido
from app.modules.HistorialPedido.model import HistorialEstadoPedido
from app.modules.FormaPago.model import FormaPago
from app.modules.Pagos.models import Pago
from app.modules.Images.model import Image
from app.modules.UnidadMedida.model import UnidadMedida



# =========================================
# ROUTERS
# =========================================

from app.modules.Ingrediente.router import router as ingrediente_router
from app.modules.Categoria.router import router as categoria_router
from app.modules.Producto.router import router as producto_router
from app.modules.DireccionEntrega.router import router as direccion_entrega_router
from app.modules.Auth.router import router as auth_router
from app.modules.Usuario.router import router as usuario_router
from app.modules.Pedido.router import router as pedido_router
from app.modules.Pagos.Router import router as pagos_router
from app.modules.Images.router import router as images_router
from app.modules.Estadisticas.router import router as estadisticas_router

# =========================================
# SEEDS
# =========================================

from app.db.seed import (
   seed_estados_pedido,
   seed_formas_pago,
   seed_roles,
   seed_usuarios
)


app = FastAPI(
   title="Segundo Parcial Backend"
)


# =========================================
# CORS
# =========================================

app.add_middleware(
   CORSMiddleware,
   allow_origins=["http://localhost:5173","http://localhost:5174",],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)


# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
def on_startup():

   SQLModel.metadata.create_all(engine)

   with Session(engine) as session:
      seed_roles(session)
      seed_estados_pedido(session)
      seed_formas_pago(session)
      seed_usuarios(session)

# =========================================
# ROUTERS
# =========================================

app.include_router(ingrediente_router)
app.include_router(categoria_router)
app.include_router(producto_router)
app.include_router(direccion_entrega_router)
app.include_router(auth_router)
app.include_router(usuario_router)
app.include_router(pedido_router)
app.include_router(pagos_router)
app.include_router(images_router)
app.include_router(estadisticas_router)