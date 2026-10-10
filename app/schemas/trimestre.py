from decimal import Decimal

from pydantic import BaseModel

from app.schemas.factura import FacturaListItem
from app.schemas.gasto import GastoAnual


class QuarterDatos(BaseModel):
    """Totales calculados de un trimestre."""

    num_facturas: int
    total_facturado: Decimal
    base_imponible: Decimal
    cuota_iva: Decimal
    cuota_irpf: Decimal
    num_gastos: int
    total_gastos: Decimal
    neto: Decimal = Decimal("0")

    def model_post_init(self, __context) -> None:
        """Resultado del trimestre: facturado - gastos."""
        self.neto = self.total_facturado - self.total_gastos


class QuarterResponse(BaseModel):
    num: int
    label: str
    months: str
    year: int
    is_current: bool
    is_future: bool
    is_past: bool
    datos: QuarterDatos
    facturas: list[FacturaListItem]
    gastos: list[GastoAnual]


class TrimestresResponse(BaseModel):
    year: int
    current_year: int
    current_quarter: int
    years: list[int]
    trimestres: list[QuarterResponse]


class DashboardQuarter(BaseModel):
    num: int
    label: str
    months: str
    is_current: bool
    facturado: Decimal
    base: Decimal
    iva: Decimal
    gastos: Decimal
    neto: Decimal
    count_facturas: int
    count_gastos: int


class DashboardResponse(BaseModel):
    year: int
    years: list[int]
    trimestres: list[DashboardQuarter]
    total_facturado: Decimal
    total_base: Decimal
    total_iva: Decimal
    total_gastos: Decimal
    total_neto: Decimal
    count_facturas: int
    count_gastos: int
    pendientes_cobro: int