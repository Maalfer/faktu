"""Configuración de tests: BD temporal aislada + clientes HTTP para la app."""

import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/opencode/test_faktu.db")
os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("SECRET_KEY", "clave-de-test-suficientemente-larga-32b")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

__all__ = ["app", "pytest_asyncio", "AsyncClient", "ASGITransport", "Base", "engine"]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    import aiosqlite

    async with aiosqlite.connect("/tmp/opencode/test_faktu.db") as con:
        for table in ("lineas_factura", "facturas", "clientes", "gastos", "config_autonomo", "users"):
            await con.execute(f"DROP TABLE IF EXISTS {table}")
        await con.commit()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth(client) -> tuple[AsyncClient, dict]:
    """Cliente autenticado con un usuario recién creado por test."""
    email = f"user{uuid.uuid4().hex[:10]}@test.es"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "clave-segura-123", "full_name": "Test User",
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers