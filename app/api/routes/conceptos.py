from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models import ConceptoTrimestre
from app.schemas.concepto import (
    ConceptoCreate,
    ConceptoRead,
    ConceptoUpdate,
    ConceptosResponse,
    QuarterConceptos,
)
from app.services.excel import generar_excel_trimestres
from app.services.libro import build_libro
from app.services.seed_conceptos import SEED_CONCEPTOS

router = APIRouter(prefix="/conceptos", tags=["conceptos"])


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


async def _get_owned(db: DbSession, user_id: int, concepto_id: int) -> ConceptoTrimestre:
    c = await db.get(ConceptoTrimestre, concepto_id)
    if not c or c.user_id != user_id:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    return c


@router.get("", response_model=ConceptosResponse)
async def get_conceptos(user: CurrentUser, db: DbSession, year: int | None = None) -> ConceptosResponse:
    await _ensure_seed(db, user.id)
    return await build_libro(db, user.id, year)


@router.get("/export")
async def export_conceptos(user: CurrentUser, db: DbSession, year: int | None = None) -> Response:
    await _ensure_seed(db, user.id)
    data = await build_libro(db, user.id, year)

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
