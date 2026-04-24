from __future__ import annotations


from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Optional, List

# ── Entrada ───────────────────────────────────────────────────────────────────

class CategoriaCreate(SQLModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: str
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None


class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class CategoriaPublic(SQLModel):
    id: int
    nombre: str
    descripcion: str
    imagen_url: Optional[str]
    parent_id: Optional[int]


class CategoriaList(SQLModel):
    data: List[CategoriaPublic]
    total: int

class CategoriaBasic(SQLModel):
    id: int
    nombre: str    

# ── Tree ────────────────────────────────────────────────────────────────────

class CategoriaTree(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    imagen_url: Optional[str]
    parent_id: Optional[int]
    subcategorias: list["CategoriaTree"] = Field(default_factory=list)

    model_config = {"from_attributes" : True}
