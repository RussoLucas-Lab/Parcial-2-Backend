from typing import List, Optional

from pydantic import EmailStr
from sqlmodel import SQLModel, Field

# ── Entrada ───────────────────────────────────────────────────────────────────

class UsuarioCreate(SQLModel):
    nombre: str = Field(min_length=3, max_length=80)
    apellido: str = Field(min_length=3, max_length=80)
    email: EmailStr
    celular: Optional[str] = Field(default=None, max_length=20)

    # En create normalmente se recibe la password en texto plano
    # y luego se transforma a hash en el service
    password: str = Field(min_length=8, max_length=100)


class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=80)
    apellido: Optional[str] = Field(default=None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    celular: Optional[str] = Field(default=None, max_length=20)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)

# ── Salida ────────────────────────────────────────────────────────────────────

class UsuarioPublic(SQLModel):
    id: int
    nombre: str
    apellido: str
    email: EmailStr
    celular: Optional[str] = None

class UsuarioList(SQLModel):
    data: List[UsuarioPublic]
    total: int

# PREGUNTAR SOBRE DONDE PONER ESTO
class Token(SQLModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int 


