"""Libro por trimestres: única fuente de verdad de ingresos y gastos.

Lo usan la página Trimestres, el Excel exportado y el Panel, de modo que todas
las cifras coinciden.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.routes.trimestres import get_quarter, quarter_order
from app.models import ConceptoTrimestre, Factura, Gasto
from app.schemas.concepto import ConceptoRead, ConceptosResponse, QuarterConceptos

MESES = ["Ene-Mar", "Abr-Jun", "Jul-Sep", "Oct-Dic"]


def _auto_concepto(**kw) -> ConceptoRead:
    return ConceptoRead(id=None, auto=True, orden=0, notas="", **kw)


async def build_libro(db, user_id: int, year: int | None) -> ConceptosResponse:
    """Libro por trimestres: se alimenta solo de Ingresos (facturas) y Gastos.

    Las facturas no borrador entran como ingreso (por su total) y cada gasto
    deducible como gasto. Los conceptos anotados a mano se suman aparte (p.ej. ventas de Stripe,
    Skool o YouTube, que no tienen factura propia).
    """
    hoy = date.today()
    current_year, current_quarter = hoy.year, get_quarter(hoy.month)

    manuales = list((await db.scalars(
        select(ConceptoTrimestre).where(ConceptoTrimestre.user_id == user_id)
    )).all())
    facturas = list((await db.scalars(
        select(Factura)
        .options(selectinload(Factura.lineas))
        .where(Factura.user_id == user_id, Factura.estado != "borrador")
        .order_by(Factura.fecha_emision, Factura.id)
    )).all())
    gastos = list((await db.scalars(
        select(Gasto).where(Gasto.user_id == user_id, Gasto.deducible.is_(True)).order_by(Gasto.fecha, Gasto.id)
    )).all())

    years = sorted(
        {r.year for r in manuales} | {f.fecha_emision.year for f in facturas} | {g.fecha.year for g in gastos},
        reverse=True,
    ) or [current_year]
    if year is None:
        year = years[0]
    if year not in years:
        years = sorted({year, *years}, reverse=True)

    trimestres: list[QuarterConceptos] = []
    for q in quarter_order(year, current_year, current_quarter):
        ingresos = [
            _auto_concepto(
                year=year, trimestre=q, tipo="ingreso", origen="factura", ref_id=f.id,
                concepto=f"Factura {f.numero_completo} · {f.receptor_nombre}"[:300],
                importe=f.total, iva=f.iva_porcentaje if f.iva_porcentaje > 0 else None,
            )
            for f in facturas
            if f.fecha_emision.year == year and f.trimestre == q and f.total > 0
        ]
        gastos_q = [
            _auto_concepto(
                year=year, trimestre=q, tipo="gasto", origen="gasto", ref_id=g.id,
                concepto=g.concepto, importe=g.importe, iva=None,
            )
            for g in gastos
            if g.fecha.year == year and g.trimestre == q and g.importe > 0
        ]
        m_rows = [r for r in manuales if r.year == year and r.trimestre == q]
        ingresos += [ConceptoRead.model_validate(r) for r in sorted(
            (r for r in m_rows if r.tipo == "ingreso"), key=lambda r: (r.orden, r.id))]
        gastos_q += [ConceptoRead.model_validate(r) for r in sorted(
            (r for r in m_rows if r.tipo == "gasto"), key=lambda r: (r.orden, r.id))]
        total_ingresos = sum((Decimal(str(c.importe)) for c in ingresos), Decimal("0"))
        total_gastos = sum((Decimal(str(c.importe)) for c in gastos_q), Decimal("0"))

        trimestres.append(QuarterConceptos(
            num=q,
            label=f"T{q}",
            months=MESES[q - 1],
            is_current=(year == current_year and q == current_quarter),
            is_future=(year == current_year and q > current_quarter) or year > current_year,
            is_past=(year == current_year and q < current_quarter) or year < current_year,
            ingresos=ingresos,
            gastos=gastos_q,
            total_ingresos=total_ingresos,
            total_gastos=total_gastos,
            neto=total_ingresos - total_gastos,
        ))

    total_ingresos = sum((q.total_ingresos for q in trimestres), Decimal("0"))
    total_gastos = sum((q.total_gastos for q in trimestres), Decimal("0"))

    return ConceptosResponse(
        year=year,
        current_year=current_year,
        current_quarter=current_quarter,
        years=years,
        trimestres=trimestres,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        total_neto=total_ingresos - total_gastos,
    )
