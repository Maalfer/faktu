import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models import Gasto
from app.schemas.gasto import GastoCreate, GastoRead, GastoUpdate

router = APIRouter(prefix="/gastos", tags=["gastos"])


async def _get_owned(db: DbSession, user_id: int, gasto_id: int) -> Gasto:
    g = await db.get(Gasto, gasto_id)
    if not g or g.user_id != user_id:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return g


@router.get("", response_model=list[GastoRead])
async def list_gastos(
    user: CurrentUser, db: DbSession, year: int | None = None, trimestre: int | None = None
) -> list[GastoRead]:
    stmt = select(Gasto).where(Gasto.user_id == user.id).order_by(Gasto.fecha.desc(), Gasto.id.desc())
    if year:
        stmt = stmt.where(Gasto.fecha >= f"{year}-01-01", Gasto.fecha <= f"{year}-12-31")
    if trimestre:
        a, b = _meses(trimestre)
        # Comparar por mes para no depender del año en el filtro de trimestre
        stmt = stmt.where(
            func.extract("month", Gasto.fecha) >= a,
            func.extract("month", Gasto.fecha) <= b,
        )
    rows = (await db.scalars(stmt)).all()
    return [GastoRead.model_validate(g) for g in rows]


def _meses(q: int) -> tuple[int, int]:
    pairs = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    return pairs.get(q, pairs[1])


@router.post("", response_model=GastoRead, status_code=status.HTTP_201_CREATED)
async def create_gasto(payload: GastoCreate, user: CurrentUser, db: DbSession) -> GastoRead:
    g = Gasto(user_id=user.id, **payload.model_dump())
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return GastoRead.model_validate(g)


@router.get("/{gasto_id}", response_model=GastoRead)
async def get_gasto(gasto_id: int, user: CurrentUser, db: DbSession) -> GastoRead:
    g = await _get_owned(db, user.id, gasto_id)
    return GastoRead.model_validate(g)


@router.put("/{gasto_id}", response_model=GastoRead)
async def update_gasto(
    gasto_id: int, payload: GastoUpdate, user: CurrentUser, db: DbSession
) -> GastoRead:
    g = await _get_owned(db, user.id, gasto_id)
    for k, v in payload.model_dump().items():
        setattr(g, k, v)
    await db.commit()
    await db.refresh(g)
    return GastoRead.model_validate(g)


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gasto(gasto_id: int, user: CurrentUser, db: DbSession) -> None:
    g = await _get_owned(db, user.id, gasto_id)
    if g.archivo:
        try:
            os.remove(settings.media_path / g.archivo)
        except OSError:
            pass
    await db.delete(g)
    await db.commit()


@router.post("/{gasto_id}/archivo", response_model=GastoRead)
async def upload_archivo(
    gasto_id: int,
    user: CurrentUser,
    db: DbSession,
    archivo: UploadFile = File(...),
) -> GastoRead:
    g = await _get_owned(db, user.id, gasto_id)
    if g.archivo:
        try:
            os.remove(settings.media_path / g.archivo)
        except OSError:
            pass

    settings.media_path.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(archivo.filename or "foto.jpg")[1].lower() or ".jpg"
    dest = Path(f"gastos/{g.id}-{uuid.uuid4().hex}{ext}")
    full = settings.media_path / dest
    full.parent.mkdir(parents=True, exist_ok=True)
    content = await archivo.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño máximo")
    full.write_bytes(content)
    g.archivo = str(dest)
    g.archivo_nombre = os.path.basename(archivo.filename or "") or f"gasto-{g.id}{ext}"
    await db.commit()
    await db.refresh(g)
    return GastoRead.model_validate(g)


@router.get("/{gasto_id}/archivo")
async def descargar_archivo(gasto_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    g = await _get_owned(db, user.id, gasto_id)
    if not g.archivo:
        raise HTTPException(status_code=404, detail="El gasto no tiene archivo adjunto")
    full = settings.media_path / g.archivo
    if not full.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(full, filename=g.archivo_nombre or os.path.basename(g.archivo))