from typing import Optional, List
from sqlmodel import SQLModel, Field



# ── Entrada ───────────────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    stock_cantidad: int = Field(default=0, ge=0)
    es_alergeno: bool = Field(default=False)

class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    es_alergeno: Optional[bool] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class IngredientePublic(SQLModel):
    id: int
    nombre: str
    stock_cantidad: int
    es_alergeno: bool

class IngredienteList(SQLModel):
    
    data: List[IngredientePublic]
    total: int

class IngredienteBasic(SQLModel):
    id: int
    nombre: str    