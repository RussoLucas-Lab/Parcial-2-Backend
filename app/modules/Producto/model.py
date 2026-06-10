from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

from app.Core.base import Base
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import BigInteger, Column, Integer, ForeignKey, Numeric, Text, Boolean

from app.modules.DetallePedido.model import DetallePedido

if TYPE_CHECKING:
    from app.modules.Categoria.model import Categoria
    from app.modules.Ingrediente.model import Ingrediente

#-------------------------------------------------------------------
#-------------- Tabla intermedia Producto Ingrediente --------------
#-------------------------------------------------------------------
class ProductoIngrediente(SQLModel, table = True):
    __tablename__ = "Producto_Ingrediente"
    producto_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("producto.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    ingrediente_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("ingrediente.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    unidad_medida_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("unidad_medida.id"),
            nullable=False
        )
    )

    es_removible: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    

#-------------------------------------------------------------------
#-------------- Tabla intermedia Producto Categoria --------------
#-------------------------------------------------------------------

class ProductoCategoria(SQLModel, table = True):
    __tablename__ = "Producto_Categoria"
    producto_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("producto.id", ondelete="CASCADE"),
            primary_key=True
        )
    )

    categoria_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("categoria.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    es_principal: bool = Field(
    sa_column=Column(Boolean, default=False, nullable=False)
    
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
 
      
#-------------------------------------------
#-------------- Tabla Producto--------------
#-------------------------------------------

class Producto(Base, table=True):
    
    nombre: str = Field(
        max_length=150,
        nullable=False
    )

    descripcion: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )

    precio_base: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False)
    )

    imagenes_url: List[str] = Field(
    default_factory=list,
    sa_column=Column(ARRAY(Text), nullable=False)
    )

    stock_cantidad: int = Field(
        default=0,
        ge=0,
        nullable=False
    )

    disponible: bool = Field(
        default=True,
        nullable=False
    )

    unidad_venta_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, ForeignKey("unidad_medida.id"), nullable=True)
    )

    #Relationships
    
    ingredientes: List["Ingrediente"] = Relationship(
        back_populates="productos",
        link_model=ProductoIngrediente
        )

    categorias: List["Categoria"] = Relationship( 
        back_populates="productos",
        link_model=ProductoCategoria
        )
    
    detalles_pedido: List["DetallePedido"] = Relationship(
        back_populates="producto",
    )