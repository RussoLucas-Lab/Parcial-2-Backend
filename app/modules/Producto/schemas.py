from sqlmodel import SQLModel, Field
from typing import Optional, List
from decimal import Decimal

from app.modules.Categoria.schemas import CategoriaBasic
from app.modules.Ingrediente.schemas import IngredienteBasic


# ── Entrada ───────────────────────────────────────────────────────────────────

class ProductoCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Decimal = Field(gt=0)
    imagenes_url: List[str] = []
    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = True

    # relaciones
    ingrediente_ids: List[int] = []
    categoria_ids: List[int] = []


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[Decimal] = Field(default=None, gt=0)
    imagenes_url: Optional[List[str]] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None

    # relaciones
    ingrediente_ids: Optional[List[int]] = None
    categoria_ids: Optional[List[int]] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class ProductoPublic(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    precio_base: Decimal
    imagenes_url: List[str]
    stock_cantidad: int
    disponible: bool

    categorias: List[CategoriaBasic]
    ingredientes: List[IngredienteBasic]


class ProductoList(SQLModel):
    data: List[ProductoPublic]
    total: int