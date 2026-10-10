from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import Factura, Gasto
from app.schemas.factura import FacturaListItem
from app.schemas.gasto import GastoAnual
from app.schemas.trimestre import QuarterDatos, QuarterResponse, TrimestresResponse

router = APIRouter(prefix="/trimestres", tags=["trimestres"])

MESES = ["Ene-Mar", "Abr-Jun", "Jul-Sep", "Oct-Dic"]


def get_quarter(month: int) -> int:
    return (month - 1) // 3 + 1


def quarter_order(year: int, current_year: int, current_quarter: int) -> list[int]:
    if year == current_year:
        past = list(range(current_quarter - 1, 0, -1))
        future = list(range(current_quarter + 1, 5))
        return [current_quarter] + past + future
    return list(range(4, 0, -1)) if year < current_year else list(range(1, 5))


def quarter_range(year: int, q: int) -> tuple[date, date]:
    start = date(year, (q - 1) * 3 + 1, 1)
    end_month = q * 3
    end = date(year, end_month, 30 if end_month in (4, 6, 9, 11) else 31)
    if end_month == 2:
        end = date(year, 2, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28)
    return start, end


async def _facturas_year(db: DbSession, user_id: int, year: int) -> list[Factura]:
    start, end = date(year, 1, 1), date(year, 12, 31)
    stmt = (
        select(Factura)
        .options(selectinload(Factura.lineas))
        .where(Factura.user_id == user_id, Factura.fecha_emision >= start, Factura.fecha_emision <= end)
        .order_by(Factura.fecha_emision)
    )
    return list((await db.scalars(stmt)).all())


async def _gastos_year(db: DbSession, user_id: int, year: int) -> list[Gasto]:
    start, end = date(year, 1, 1), date(year, 12, 31)
    stmt = (
        select(Gasto)
        .where(Gasto.user_id == user_id, Gasto.fecha >= start, Gasto.fecha <= end)
        .order_by(Gasto.fecha)
    )
    return list((await db.scalars(stmt)).all())


@router.get("", response_model=TrimestresResponse)
async def get_trimestres(user: CurrentUser, db: DbSession, year: int | None = None) -> TrimestresResponse:
    hoy = date.today()
    current_year, current_quarter = hoy.year, get_quarter(hoy.month)

    years = sorted(
        set((await db.scalars(select(Factura.fecha_emision).where(Factura.user_id == user.id))).all())
        | set((await db.scalars(select(Gasto.fecha).where(Gasto.user_id == user.id))).all()),
    )
    years = sorted({d.year for d in years}, reverse=True) if years else [current_year]
    if year is None:
        year = max(years) if years else current_year
    if year not in years:
        years = [year, *[y for y in years if y != year]]

    facturas = await _facturas_year(db, user.id, year)
    gastos = await _gastos_year(db, user.id, year)

    trimestres: list[QuarterResponse] = []
    for q in quarter_order(year, current_year, current_quarter):
        start, end = quarter_range(year, q)
        qf = [f for f in facturas if start <= f.fecha_emision <= end]
        qg = [g for g in gastos if start <= g.fecha <= end]

        total_facturado = sum((f.total for f in qf), Decimal("0"))
        base = sum((f.base_imponible for f in qf), Decimal("0"))
        iva = sum((f.cuota_iva for f in qf), Decimal("0"))
        irpf = sum((f.cuota_irpf for f in qf), Decimal("0"))
        total_gastos = sum((g.importe for g in qg if g.deducible), Decimal("0"))

        is_current = year == current_year and q == current_quarter
        is_future = (year == current_year and q > current_quarter) or year > current_year
        is_past = (year == current_year and q < current_quarter) or year < current_year

        trimestres.append(QuarterResponse(
            num=q,
            label=f"T{q}",
            months=MESES[q - 1],
            year=year,
            is_current=is_current,
            is_future=is_future,
            is_past=is_past,
            datos=QuarterDatos(
                num_facturas=len(qf),
                total_facturado=total_facturado,
                base_imponible=base,
                cuota_iva=iva,
                cuota_irpf=irpf,
                num_gastos=sum(1 for g in qg if g.deducible),
                total_gastos=total_gastos,
            ),
            facturas=[FacturaListItem.model_validate(f) for f in qf],
            gastos=[GastoAnual.model_validate(g) for g in qg],
        ))

    return TrimestresResponse(
        year=year,
        current_year=current_year,
        current_quarter=current_quarter,
        years=years,
        trimestres=trimestres,
    )