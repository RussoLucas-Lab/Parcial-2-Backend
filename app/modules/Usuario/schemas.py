from typing import List, Optional
from pydantic import EmailStr
from sqlmodel import SQLModel, Field
from app.modules.DireccionEntrega.schemas import DireccionEntregaPublic


class UsuarioCreate(SQLModel):
    nombre: str = Field(min_length=3, max_length=80)
    apellido: str = Field(min_length=3, max_length=80)
    email: EmailStr
    celular: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=100)

# Utilizado para crear un usuario junto con sus roles asignados
class UsuarioCreateConRoles(UsuarioCreate):
    roles: list[str] = Field(..., min_items=1)


class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=3, max_length=80)
    apellido: Optional[str] = Field(default=None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    celular: Optional[str] = Field(default=None, max_length=20)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)


class UsuarioPublic(SQLModel):
    id: int
    nombre: str
    apellido: str
    email: EmailStr
    celular: Optional[str] = None
    activo: bool
    roles: List[str] = []
    direcciones: List[DireccionEntregaPublic] = []


class UsuarioList(SQLModel):
    data: List[UsuarioPublic]
    total: int


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RolAsignarRequest(SQLModel):
    rol_codigo: str = Field(max_length=20)

class RolesAsignarRequest(SQLModel):
    roles: list[str] = Field(..., min_items=1, max_items=5)
