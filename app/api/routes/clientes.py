from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Cliente, LineaFactura, Factura
from app.schemas.cliente import ClienteCreate, ClienteRead, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["clientes"])


class ClienteConStats(ClienteRead):
    total_facturado: Decimal = Field(default=Decimal("0"))
    num_facturas: int = 0


def _base_imponible_subquery():
    """Subconsulta: suma de importes de las líneas de cada factura."""
    return (
        select(func.sum(LineaFactura.cantidad * LineaFactura.precio_unitario))
        .where(LineaFactura.factura_id == Factura.id)
        .correlate(Factura)
        .scalar_subquery()
    )


def _total_factura_expr():
    base = _base_imponible_subquery()
    return func.coalesce(
        base + Factura.iva_porcentaje / 100 * base - Factura.irpf_porcentaje / 100 * base,
        0,
    )


@router.get("", response_model=list[ClienteConStats])
async def list_clientes(user: CurrentUser, db: DbSession, q: str = "") -> list[ClienteConStats]:
    """Clientes del usuario con total facturado acumulado."""
    stmt = (
        select(
            Cliente,
            func.coalesce(func.sum(_total_factura_expr()), 0).label("total_facturado"),
            func.count(Factura.id).label("num_facturas"),
        )
        .outerjoin(Factura, Factura.cliente_id == Cliente.id)
        .where(Cliente.user_id == user.id)
        .group_by(Cliente.id)
        .order_by(func.lower(Cliente.nombre))
    )
    if q.strip():
        stmt = stmt.where(Cliente.nombre.ilike(f"%{q.strip()}%"))
    rows = (await db.execute(stmt)).all()
    out = []
    for c, total, num in rows:
        item = ClienteConStats(**ClienteRead.model_validate(c).model_dump())
        item.total_facturado = Decimal(total)
        item.num_facturas = num
        out.append(item)
    return out


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def create_cliente(payload: ClienteCreate, user: CurrentUser, db: DbSession) -> ClienteRead:
    c = Cliente(user_id=user.id, **payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ClienteRead.model_validate(c)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def get_cliente(cliente_id: int, user: CurrentUser, db: DbSession) -> ClienteRead:
    c = await db.get(Cliente, cliente_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ClienteRead.model_validate(c)


@router.put("/{cliente_id}", response_model=ClienteRead)
async def update_cliente(
    cliente_id: int, payload: ClienteUpdate, user: CurrentUser, db: DbSession
) -> ClienteRead:
    c = await db.get(Cliente, cliente_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return ClienteRead.model_validate(c)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cliente(cliente_id: int, user: CurrentUser, db: DbSession) -> None:
    c = await db.get(Cliente, cliente_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await db.delete(c)
    await db.commit()