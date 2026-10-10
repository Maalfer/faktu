from typing import Annotated
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    API_TOKEN_PREFIX,
    decode_access_token,
    parse_api_token,
    verify_api_secret,
)
from app.models import ApiToken, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_api_token(db: AsyncSession, token: str) -> User | None:
    parsed = parse_api_token(token)
    if not parsed:
        return None
    prefix, secret = parsed
    row = await db.scalar(
        select(ApiToken).where(
            ApiToken.prefix == prefix,
            ApiToken.revoked_at.is_(None),
        )
    )
    if not row or not verify_api_secret(secret, row.hashed_secret):
        return None
    row.last_used_at = datetime.now(timezone.utc)
    user = await db.get(User, row.user_id)
    return user if (user and user.is_active) else None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token.startswith(API_TOKEN_PREFIX):
        user = await _user_from_api_token(db, token)
        if user is None:
            raise credentials_exc
        return user

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise credentials_exc

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    user = await db.scalar(select(User).where(User.id == int(user_id)))
    if user is None or not user.is_active:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]