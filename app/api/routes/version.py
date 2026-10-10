"""Información de versión expuesta a la SPA."""
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.version import VersionInfo

router = APIRouter(tags=["meta"])


@router.get("/version", response_model=VersionInfo)
async def get_version() -> VersionInfo:
    return VersionInfo(name=settings.app_name, version=settings.app_version)
