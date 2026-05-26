from typing import List, Optional
from decimal import Decimal

from sqlmodel import SQLModel, Field


# ── Entrada ───────────────────────────────────────────────────────────────────

class DireccionEntregaCreate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str
    linea2: Optional[str] = None
    ciudad: str = Field(max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool = False


class DireccionEntregaUpdate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: Optional[str] = None
    linea2: Optional[str] = None
    ciudad: Optional[str] = Field(default=None, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None

    
    es_principal: Optional[bool] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class DireccionEntregaPublic(SQLModel):
    id: int
    usuario_id: int
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool


class DireccionEntregaList(SQLModel):
    data: List[DireccionEntregaPublic]
    total: int
