from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.api.routes.trimestres import get_quarter, quarter_order, quarter_range
from app.models import Factura, Gasto
from app.schemas.trimestre import DashboardQuarter, DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(user: CurrentUser, db: DbSession, year: int | None = None) -> DashboardResponse:
    hoy = date.today()
    current_year, current_quarter = hoy.year, get_quarter(hoy.month)

    factura_years = (await db.scalars(select(Factura.fecha_emision).where(Factura.user_id == user.id))).all()
    gasto_years = (await db.scalars(select(Gasto.fecha).where(Gasto.user_id == user.id))).all()
    years = sorted({d.year for d in factura_years} | {d.year for d in gasto_years}, reverse=True)
    if year is None:
        year = years[0] if years else current_year

    start, end = date(year, 1, 1), date(year, 12, 31)

    facturas = (await db.scalars(select(Factura).options(selectinload(Factura.lineas)).where(
        Factura.user_id == user.id, Factura.fecha_emision >= start, Factura.fecha_emision <= end))).all()
    gastos = (await db.scalars(select(Gasto).where(
        Gasto.user_id == user.id, Gasto.fecha >= start, Gasto.fecha <= end))).all()

    trimestres: list[DashboardQuarter] = []
    for q in quarter_order(year, current_year, current_quarter):
        qs, qe = quarter_range(year, q)
        qf = [f for f in facturas if qs <= f.fecha_emision <= qe]
        qg = [g for g in gastos if qs <= g.fecha <= qe]
        facturado = sum((f.total for f in qf), Decimal("0"))
        base = sum((f.base_imponible for f in qf), Decimal("0"))
        iva = sum((f.cuota_iva for f in qf), Decimal("0"))
        gasto_total = sum((g.importe for g in qg), Decimal("0"))
        trimestres.append(DashboardQuarter(
            num=q,
            label=f"T{q}",
            months=["Ene-Mar", "Abr-Jun", "Jul-Sep", "Oct-Dic"][q - 1],
            is_current=(year == current_year and q == current_quarter),
            facturado=facturado,
            base=base,
            iva=iva,
            gastos=gasto_total,
            neto=facturado - gasto_total,
            count_facturas=len(qf),
            count_gastos=len(qg),
        ))

    total_facturado = sum((q.facturado for q in trimestres), Decimal("0"))
    total_base = sum((q.base for q in trimestres), Decimal("0"))
    total_iva = sum((q.iva for q in trimestres), Decimal("0"))
    total_gastos = sum((q.gastos for q in trimestres), Decimal("0"))
    total_neto = total_facturado - total_gastos
    pendientes = sum(1 for f in facturas if f.estado in ("emitida", "borrador"))

    return DashboardResponse(
        year=year,
        years=sorted(set(years) | {year}, reverse=True),
        trimestres=trimestres,
        total_facturado=total_facturado,
        total_base=total_base,
        total_iva=total_iva,
        total_gastos=total_gastos,
        total_neto=total_neto,
        count_facturas=sum(q.count_facturas for q in trimestres),
        count_gastos=sum(q.count_gastos for q in trimestres),
        pendientes_cobro=pendientes,
    )