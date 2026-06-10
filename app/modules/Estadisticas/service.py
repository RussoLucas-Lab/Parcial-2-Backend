from app.modules.Estadisticas.enum import PeriodoEnum
from app.modules.Estadisticas.unit_of_work import EstadisticaUnitOfWork


class EstadisticaService:

    def __init__(self, uow: EstadisticaUnitOfWork):
        self.uow = uow

    def _obtener_dias(self, periodo: PeriodoEnum) -> int:

        dias_por_periodo = {
            PeriodoEnum.SEMANA: 7,
            PeriodoEnum.MES: 30,
        }

        return dias_por_periodo[periodo]

   
    # ─── KPIs ─────────────────────────────────────────────────────────────
    

    def get_facturacion_total(self):
        return self.uow.pedidos.get_facturacion_total()

    def get_cantidad_pedidos(self):
        return self.uow.pedidos.get_cantidad_pedidos()

    # ─── Gráficos ─────────────────────────────────────────────────────────────

    def get_facturacion_por_periodo(
        self,
        periodo: PeriodoEnum
    ):

        dias = self._obtener_dias(periodo)

        return self.uow.pedidos.get_facturacion_por_periodo(
            dias
        )

    def get_pedidos_por_periodo(
        self,
        periodo: PeriodoEnum
    ):

        dias = self._obtener_dias(periodo)

        return self.uow.pedidos.get_pedidos_por_periodo(
            dias
        )
    
    def get_top_productos(
        self,
        limit: int = 10
    ):

        return self.uow.detalles_pedido.get_top_productos(
            limit
        )