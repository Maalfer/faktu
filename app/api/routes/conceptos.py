from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Body, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.api.routes.trimestres import get_quarter, quarter_order, quarter_range
from app.core.config import settings
from app.models import ConceptoTrimestre, Factura, Gasto
from app.schemas.concepto import (
    ConceptoCreate,
    ConceptoRead,
    ConceptoUpdate,
    ConceptosResponse,
    GenerarPayload,
    GenerarResponse,
    QuarterConceptos,
)
from app.services.excel import generar_excel_trimestres
from app.services.seed_conceptos import SEED_CONCEPTOS

router = APIRouter(prefix="/conceptos", tags=["conceptos"])

MESES = ["Ene-Mar", "Abr-Jun", "Jul-Sep", "Oct-Dic"]


async def _ensure_seed(db: DbSession, user_id: int) -> None:
    """Carga los conceptos iniciales (T1 y T2) si el usuario aún no tiene ninguno."""
    if not settings.seed_conceptos or not SEED_CONCEPTOS:
        return

    total = await db.scalar(
        select(func.count()).select_from(ConceptoTrimestre).where(ConceptoTrimestre.user_id == user_id)
    )
    if total:
        return

    year = date.today().year
    for q, data in SEED_CONCEPTOS.items():
        for i, (concepto, importe, iva) in enumerate(data["ingresos"]):
            db.add(ConceptoTrimestre(
                user_id=user_id, year=year, trimestre=q, tipo="ingreso",
                concepto=concepto, importe=importe, iva=iva, orden=i,
            ))
        for i, (concepto, importe) in enumerate(data["gastos"]):
            db.add(ConceptoTrimestre(
                user_id=user_id, year=year, trimestre=q, tipo="gasto",
                concepto=concepto, importe=importe, iva=None, orden=i,
            ))
    await db.commit()


async def _build_response(db: DbSession, user_id: int, year: int | None) -> ConceptosResponse:
    hoy = date.today()
    current_year, current_quarter = hoy.year, get_quarter(hoy.month)

    rows = list((await db.scalars(
        select(ConceptoTrimestre).where(ConceptoTrimestre.user_id == user_id)
    )).all())

    years = sorted({r.year for r in rows}, reverse=True) or [current_year]
    if year is None:
        year = years[0]
    if year not in years:
        years = sorted({year, *years}, reverse=True)

    year_rows = [r for r in rows if r.year == year]

    trimestres: list[QuarterConceptos] = []
    for q in quarter_order(year, current_year, current_quarter):
        q_rows = [r for r in year_rows if r.trimestre == q]
        ingresos = sorted((r for r in q_rows if r.tipo == "ingreso"), key=lambda r: (r.orden, r.id))
        gastos = sorted((r for r in q_rows if r.tipo == "gasto"), key=lambda r: (r.orden, r.id))
        total_ingresos = sum((r.importe for r in ingresos), Decimal("0"))
        total_gastos = sum((r.importe for r in gastos), Decimal("0"))

        trimestres.append(QuarterConceptos(
            num=q,
            label=f"T{q}",
            months=MESES[q - 1],
            is_current=(year == current_year and q == current_quarter),
            is_future=(year == current_year and q > current_quarter) or year > current_year,
            is_past=(year == current_year and q < current_quarter) or year < current_year,
            ingresos=[ConceptoRead.model_validate(r) for r in ingresos],
            gastos=[ConceptoRead.model_validate(r) for r in gastos],
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


async def _get_owned(db: DbSession, user_id: int, concepto_id: int) -> ConceptoTrimestre:
    c = await db.get(ConceptoTrimestre, concepto_id)
    if not c or c.user_id != user_id:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    return c


@router.get("", response_model=ConceptosResponse)
async def get_conceptos(user: CurrentUser, db: DbSession, year: int | None = None) -> ConceptosResponse:
    await _ensure_seed(db, user.id)
    return await _build_response(db, user.id, year)


@router.get("/export")
async def export_conceptos(user: CurrentUser, db: DbSession, year: int | None = None) -> Response:
    await _ensure_seed(db, user.id)
    data = await _build_response(db, user.id, year)

    trimestres = [
        {
            "num": q.num,
            "ingresos": [(c.concepto, c.importe, c.iva) for c in q.ingresos],
            "gastos": [(c.concepto, c.importe) for c in q.gastos],
        }
        for q in sorted(data.trimestres, key=lambda q: q.num)
    ]
    content = generar_excel_trimestres(data.year, trimestres)
    filename = f"Trimestres_{data.year}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=ConceptoRead, status_code=status.HTTP_201_CREATED)
async def create_concepto(payload: ConceptoCreate, user: CurrentUser, db: DbSession) -> ConceptoRead:
    c = ConceptoTrimestre(user_id=user.id, **payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ConceptoRead.model_validate(c)


@router.post("/generar", response_model=GenerarResponse)
async def generar_conceptos(
    user: CurrentUser,
    db: DbSession,
    payload: GenerarPayload = Body(...),
) -> GenerarResponse:
    """Rellena el libro de un trimestre a partir de las facturas emitidas y los gastos.

    Es idempotente: solo añade lo que todavía no tiene su concepto vinculado
    (``factura_id`` / ``gasto_id``). Los conceptos anotados a mano no se tocan.
    Las facturas en borrador se ignoran. El importe es el total de la factura
    (lo realmente cobrado) y el de cada gasto.
    """
    start, end = quarter_range(payload.year, payload.trimestre)

    facturas = (await db.scalars(
        select(Factura)
        .options(selectinload(Factura.lineas))
        .where(
            Factura.user_id == user.id,
            Factura.estado != "borrador",
            Factura.fecha_emision >= start,
            Factura.fecha_emision <= end,
        )
        .order_by(Factura.fecha_emision, Factura.id)
    )).all()
    gastos = (await db.scalars(
        select(Gasto)
        .where(Gasto.user_id == user.id, Gasto.fecha >= start, Gasto.fecha <= end)
        .order_by(Gasto.fecha, Gasto.id)
    )).all()

    existentes = (await db.scalars(
        select(ConceptoTrimestre).where(
            ConceptoTrimestre.user_id == user.id,
            ConceptoTrimestre.year == payload.year,
            ConceptoTrimestre.trimestre == payload.trimestre,
        )
    )).all()
    facturas_ok = {c.factura_id for c in existentes if c.factura_id}
    gastos_ok = {c.gasto_id for c in existentes if c.gasto_id}
    orden_ing = max((c.orden for c in existentes if c.tipo == "ingreso"), default=-1) + 1
    orden_gas = max((c.orden for c in existentes if c.tipo == "gasto"), default=-1) + 1

    nuevos_ing = nuevos_gas = 0
    for f in facturas:
        if f.id in facturas_ok or f.total <= 0:
            continue
        db.add(ConceptoTrimestre(
            user_id=user.id, year=payload.year, trimestre=payload.trimestre, tipo="ingreso",
            concepto=f"Factura {f.numero_completo} · {f.receptor_nombre}"[:300],
            importe=f.total, iva=f.iva_porcentaje if f.iva_porcentaje > 0 else None,
            orden=orden_ing, factura_id=f.id,
        ))
        orden_ing += 1
        nuevos_ing += 1
    for g in gastos:
        if g.id in gastos_ok or g.importe <= 0:
            continue
        db.add(ConceptoTrimestre(
            user_id=user.id, year=payload.year, trimestre=payload.trimestre, tipo="gasto",
            concepto=g.concepto[:300], importe=g.importe, iva=None,
            orden=orden_gas, gasto_id=g.id,
        ))
        orden_gas += 1
        nuevos_gas += 1
    await db.commit()
    return GenerarResponse(ingresos_nuevos=nuevos_ing, gastos_nuevos=nuevos_gas)


@router.get("/{concepto_id}", response_model=ConceptoRead)
async def get_concepto(concepto_id: int, user: CurrentUser, db: DbSession) -> ConceptoRead:
    c = await _get_owned(db, user.id, concepto_id)
    return ConceptoRead.model_validate(c)


@router.put("/{concepto_id}", response_model=ConceptoRead)
async def update_concepto(
    concepto_id: int, payload: ConceptoUpdate, user: CurrentUser, db: DbSession
) -> ConceptoRead:
    c = await _get_owned(db, user.id, concepto_id)
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return ConceptoRead.model_validate(c)


@router.delete("/{concepto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concepto(concepto_id: int, user: CurrentUser, db: DbSession) -> None:
    c = await _get_owned(db, user.id, concepto_id)
    await db.delete(c)
    await db.commit()
