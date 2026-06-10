from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.deps import require_role
from app.Core.deps import require_role
from app.modules.Estadisticas.enum import PeriodoEnum
from app.modules.Estadisticas.service import EstadisticaService
from app.modules.Estadisticas.unit_of_work import EstadisticaUnitOfWork

router = APIRouter(prefix="/estadisticas",tags=["Estadísticas"],dependencies=[
        Depends(require_role(["ADMIN"]))
    ])


def get_estadistica_service(
    session: Session = Depends(get_session)
) -> EstadisticaService:

    uow = EstadisticaUnitOfWork(session)

    return EstadisticaService(uow)

@router.get("/facturacion-total")
def facturacion_total(
    service: EstadisticaService = Depends(get_estadistica_service)
):
    return service.get_facturacion_total()


@router.get("/cantidad-pedidos")
def cantidad_pedidos(
    service: EstadisticaService = Depends(get_estadistica_service)
):
    return service.get_cantidad_pedidos()


@router.get("/facturacion")
def facturacion_por_periodo(
    periodo: PeriodoEnum,
    service: EstadisticaService = Depends(get_estadistica_service)
):
    return service.get_facturacion_por_periodo(periodo)


@router.get("/pedidos")
def pedidos_por_periodo(
    periodo: PeriodoEnum,
    service: EstadisticaService = Depends(get_estadistica_service)
):
    return service.get_pedidos_por_periodo(periodo)

@router.get("/top-productos")
def top_productos(
    service: EstadisticaService = Depends(
        get_estadistica_service
    )
):
    return service.get_top_productos()