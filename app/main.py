from fastapi import FastAPI
from sqlmodel import SQLModel
from app.Core.database import engine


from app.Categoria.model import Categoria
from app.Ingrediente.model import Ingrediente
from app.Producto.model import Producto, ProductoIngrediente, ProductoCategoria

from app.Ingrediente.router import router as ingrediente_router
from app.Categoria.router import router as categoria_router
from app.Producto.router import router as producto_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Primer Parcial: API Producto, Categoreia e Ingrediente")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(ingrediente_router)
app.include_router(categoria_router)
app.include_router(producto_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
