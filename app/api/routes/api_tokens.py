"""CRUD de tokens de API personales (uso con IAs / integraciones externas)."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import generate_api_token, hash_api_secret
from app.models import ApiToken
from app.schemas.api_token import ApiTokenCreate, ApiTokenCreated, ApiTokenRead

router = APIRouter(prefix="/api-tokens", tags=["api-tokens"])


@router.get("", response_model=list[ApiTokenRead])
async def list_tokens(user: CurrentUser, db: DbSession) -> list[ApiTokenRead]:
    rows = (
        await db.scalars(
            select(ApiToken)
            .where(ApiToken.user_id == user.id)
            .order_by(ApiToken.created_at.desc())
        )
    ).all()
    return [ApiTokenRead.model_validate(r) for r in rows]


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    payload: ApiTokenCreate, user: CurrentUser, db: DbSession
) -> ApiTokenCreated:
    # Si ya existe uno con el mismo prefix (improbable), reintentar.
    for _ in range(3):
        token, prefix, secret = generate_api_token()
        exists = await db.scalar(select(ApiToken).where(ApiToken.prefix == prefix))
        if not exists:
            break
    else:  # pragma: no cover - extremadamente improbable
        raise HTTPException(status_code=500, detail="No se pudo generar un token único")

    row = ApiToken(
        user_id=user.id,
        name=(payload.name or "").strip()[:80],
        prefix=prefix,
        hashed_secret=hash_api_secret(secret),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return ApiTokenCreated(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        token=token,
        created_at=row.created_at,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(token_id: int, user: CurrentUser, db: DbSession) -> None:
    row = await db.get(ApiToken, token_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Token no encontrado")
    row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
