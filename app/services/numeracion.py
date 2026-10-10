"""Numeración automática de facturas por año (p.ej. 03/2026)."""
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Factura

_NUM_RE = re.compile(r"^(\d+)")


async def next_numero(db: AsyncSession, user_id: int, year: int, serie: str = "") -> str:
    """Calcula el siguiente número de factura para el usuario, año y serie."""
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    stmt = select(Factura.numero).where(
        Factura.user_id == user_id,
        Factura.serie == serie,
        Factura.fecha_emision >= start,
        Factura.fecha_emision <= end,
    )
    numeros = (await db.scalars(stmt)).all()

    max_n = 0
    for raw in numeros:
        m = _NUM_RE.match(raw or "")
        if m:
            try:
                max_n = max(max_n, int(m.group(1)))
            except ValueError:
                continue
    return f"{max_n + 1:02d}/{year}"