from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, Relationship
from typing import TYPE_CHECKING, Optional, List
from app.Core.base import Base

from app.modules.Producto.model import ProductoCategoria
if TYPE_CHECKING:
    from app.modules.Producto.model import Producto

class Categoria(Base, table= True):
    nombre: str = Field(min_length=3, max_length=100, unique = True, nullable= False)
    descripcion: str = Field(nullable= False)
    imagen_url: Optional[str] = Field(nullable= True)

    parent_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("categoria.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    #------Relacion N:N con Productos------
    productos: List["Producto"] = Relationship( back_populates="categorias", link_model=ProductoCategoria)