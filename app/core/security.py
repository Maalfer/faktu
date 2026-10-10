"""Seguridad: hash de contraseñas y tokens JWT."""
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import bcrypt
import jwt

from app.core.config import settings

API_TOKEN_PREFIX = "fkt_"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str | int, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Devuelve el payload del token o lanza jwt.PyJWTError si es inválido."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def hash_api_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_secret(secret: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(secret.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_api_token() -> tuple[str, str, str]:
    """Devuelve (token_completo, prefix, secret).

    El token tiene el formato `fkt_<prefix>_<secret>`. Solo el `secret` se
    persiste hasheado; el `prefix` se guarda en claro para identificar el
    token en listados.
    """
    prefix = token_urlsafe(6)[:8]
    secret = token_urlsafe(32)
    token = f"{API_TOKEN_PREFIX}{prefix}_{secret}"
    return token, prefix, secret


def parse_api_token(token: str) -> tuple[str, str] | None:
    """Devuelve (prefix, secret) si el token tiene el formato correcto."""
    if not token or not token.startswith(API_TOKEN_PREFIX):
        return None
    body = token[len(API_TOKEN_PREFIX):]
    if "_" not in body:
        return None
    prefix, _, secret = body.partition("_")
    if not prefix or not secret:
        return None
    return prefix, secret
