"""Faktu — Aplicación FastAPI de gestión de facturas y gastos para autónomos."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth,
    clientes,
    configuracion,
    dashboard,
    facturas,
    gastos,
    trimestres,
)
from app.core.config import settings
from app.core.database import Base, engine

logger = logging.getLogger("faktu")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.media_path.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        # Arranque cero-config: crea las tablas si no existen (SQLite/desarrollo).
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Gestión de facturas y gastos para autónomos, por trimestres.",
    lifespan=lifespan,
)

# CORS: para desarrollo del SPA desde otro origen.
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Rutas API ────────────────────────────────────────────────────────────────
for r in (auth, clientes, facturas, gastos, configuracion, trimestres, dashboard):
    app.include_router(r.router, prefix=settings.api_prefix)


# ── Estáticos y SPA ──────────────────────────────────────────────────────────
settings.media_path.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
app.mount("/media", StaticFiles(directory=settings.media_path), name="media")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Portada de la SPA."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{_:path}", include_in_schema=False)
async def spa_fallback(_: str) -> FileResponse:
    """Cualquier otra ruta que no sea API sirve la SPA (router limpi en cliente)."""
    return FileResponse(STATIC_DIR / "index.html")