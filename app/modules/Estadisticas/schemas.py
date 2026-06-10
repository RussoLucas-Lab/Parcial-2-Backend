from decimal import Decimal


from pydantic import BaseModel
from enum import Enum


class PeriodoEnum(str, Enum):
    SEMANA = "semana"
    MES = "mes"
    
class FacturacionPeriodoResponse(BaseModel):
    fecha: str
    total: Decimal

class PedidoPeriodoResponse(BaseModel):
    fecha: str
    cantidad: int

class TopProductoResponse(BaseModel):
    producto: str
    cantidad: int

class DashboardResponse(BaseModel):
    facturacion_total: Decimal
    cantidad_pedidos: int