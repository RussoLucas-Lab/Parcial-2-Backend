from sqlmodel import Field, Relationship
from app.Core.base import Base
from typing import TYPE_CHECKING, Optional, List
from app.modules.Producto.model import ProductoIngrediente

if TYPE_CHECKING:
    from app.modules.Producto.model import Producto

class Ingrediente(Base, table= True):
    
    nombre: str = Field(
        max_length=100,
        nullable=False,
        unique=True
    )
    
    descripcion: Optional[str] = Field(default=None)

    es_alergeno: bool = Field(
        default=False,
        nullable=False
    )

    #------ Relacion N:N con Productos ------

    productos: List["Producto"] = Relationship(back_populates="ingredientes", link_model= ProductoIngrediente)
    