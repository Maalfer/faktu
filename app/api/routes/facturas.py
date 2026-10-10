import io
import re
import zipfile
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.api.routes.trimestres import quarter_range
from app.models import Cliente, Factura, LineaFactura
from app.schemas.factura import (
    FacturaCreate,
    FacturaListItem,
    FacturaRead,
    FacturaUpdate,
    NextNumeroResponse,
)
from app.services.numeracion import next_numero
from app.services.pdf import generar_pdf_factura

router = APIRouter(prefix="/facturas", tags=["facturas"])


def _load_options():
    return (
        selectinload(Factura.lineas),
        selectinload(Factura.cliente),
    )


async def _get_owned(db: DbSession, user_id: int, factura_id: int) -> Factura:
    stmt = (
        select(Factura)
        .options(*_load_options())
        .where(Factura.id == factura_id, Factura.user_id == user_id)
    )
    f = await db.scalar(stmt)
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return f


async def _apply_payload(db: DbSession, factura: Factura, payload: FacturaCreate | FacturaUpdate, user_id: int) -> None:
    data = payload.model_dump(exclude={"lineas"})

    if payload.cliente_id is not None:
        k = await db.get(Cliente, payload.cliente_id)
        if not k or k.user_id != user_id:
            raise HTTPException(status_code=422, detail="Cliente no válido")

    # Numeración correlativa: no se admiten dos facturas con el mismo número en la misma serie y año
    if factura.id is None or (factura.numero, factura.serie, factura.fecha_emision.year) != (
        payload.numero, payload.serie, payload.fecha_emision.year
    ):
        repetida = await db.scalar(select(func.count()).select_from(Factura).where(
            Factura.user_id == user_id, Factura.numero == payload.numero, Factura.serie == payload.serie,
            Factura.fecha_emision >= date(payload.fecha_emision.year, 1, 1),
            Factura.fecha_emision <= date(payload.fecha_emision.year, 12, 31),
            Factura.id != (factura.id or 0),
        ))
        if repetida:
            raise HTTPException(status_code=409, detail=f"Ya existe una factura con el número {payload.serie}{payload.numero} en {payload.fecha_emision.year}")

    for k, v in data.items():
        setattr(factura, k, v)

    # Reemplazar líneas
    factura.lineas.clear()
    await db.flush()
    for i, linea in enumerate(payload.lineas):
        factura.lineas.append(LineaFactura(**linea.model_dump(exclude={"orden"}), orden=i))


@router.get("/zip")
async def descargar_zip_trimestre(
    user: CurrentUser, db: DbSession, year: int = Query(ge=2000, le=2100), trimestre: int = Query(ge=1, le=4)
) -> Response:
    """ZIP con el PDF de todas las facturas (no borrador) emitidas en un trimestre."""
    start, end = quarter_range(year, trimestre)
    facturas = (await db.scalars(
        select(Factura)
        .options(*_load_options())
        .where(
            Factura.user_id == user.id,
            Factura.estado != "borrador",
            Factura.fecha_emision >= start,
            Factura.fecha_emision <= end,
        )
        .order_by(Factura.fecha_emision, Factura.id)
    )).all()
    if not facturas:
        raise HTTPException(status_code=404, detail="No hay facturas en ese trimestre")

    out = io.BytesIO()
    usados: set[str] = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in facturas:
            base = re.sub(r'[\\/:*?"<>|]+', "-", f"Factura {f.numero_completo} - {f.receptor_nombre}").strip()[:120]
            nombre, n = f"{base}.pdf", 2
            while nombre in usados:
                nombre, n = f"{base} ({n}).pdf", n + 1
            usados.add(nombre)
            zf.writestr(nombre, generar_pdf_factura(f))
    return Response(
        content=out.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="facturas_{year}_T{trimestre}.zip"'},
    )


@router.get("/next-numero", response_model=NextNumeroResponse)
async def get_next_numero(user: CurrentUser, db: DbSession, year: int) -> NextNumeroResponse:
    """Siguiente número disponible para el año indicado."""
    numero = await next_numero(db, user.id, year)
    return NextNumeroResponse(numero=numero, serie="")  # la serie se decide al crear


@router.get("", response_model=list[FacturaListItem])
async def list_facturas(
    user: CurrentUser, db: DbSession, year: int | None = None, trimestre: int | None = None
) -> list[FacturaListItem]:
    stmt = (
        select(Factura)
        .options(*_load_options())
        .where(Factura.user_id == user.id)
        .order_by(Factura.fecha_emision.desc(), Factura.id.desc())
    )
    if year:
        stmt = stmt.where(Factura.fecha_emision >= f"{year}-01-01", Factura.fecha_emision <= f"{year}-12-31")
    if trimestre:
        a, b = trimestre_months(trimestre)
        stmt = stmt.where(
            func.extract("month", Factura.fecha_emision) >= a,
            func.extract("month", Factura.fecha_emision) <= b,
        )
    rows = (await db.scalars(stmt)).all()
    return [FacturaListItem.model_validate(f) for f in rows]


def trimestre_months(q: int) -> tuple[int, int]:
    pairs = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    return pairs.get(q, pairs[1])


@router.post("", response_model=FacturaRead, status_code=status.HTTP_201_CREATED)
async def create_factura(payload: FacturaCreate, user: CurrentUser, db: DbSession) -> FacturaRead:
    f = Factura(user_id=user.id)
    await _apply_payload(db, f, payload, user.id)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    stmt = select(Factura).options(*_load_options()).where(Factura.id == f.id)
    f = await db.scalar(stmt)
    return FacturaRead.model_validate(f)


@router.get("/{factura_id}", response_model=FacturaRead)
async def get_factura(factura_id: int, user: CurrentUser, db: DbSession) -> FacturaRead:
    f = await _get_owned(db, user.id, factura_id)
    return FacturaRead.model_validate(f)


@router.put("/{factura_id}", response_model=FacturaRead)
async def update_factura(
    factura_id: int, payload: FacturaUpdate, user: CurrentUser, db: DbSession
) -> FacturaRead:
    f = await _get_owned(db, user.id, factura_id)
    await _apply_payload(db, f, payload, user.id)
    await db.commit()
    f = await _get_owned(db, user.id, factura_id)
    return FacturaRead.model_validate(f)


@router.delete("/{factura_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_factura(factura_id: int, user: CurrentUser, db: DbSession) -> None:
    f = await _get_owned(db, user.id, factura_id)
    await db.delete(f)
    await db.commit()


@router.get("/{factura_id}/pdf")
async def descargar_pdf_factura(factura_id: int, user: CurrentUser, db: DbSession) -> Response:
    f = await _get_owned(db, user.id, factura_id)
    pdf = generar_pdf_factura(f)
    filename = f"factura_{f.numero_completo.replace('/', '-')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )