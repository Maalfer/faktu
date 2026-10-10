from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import ConfigAutonomo
from app.schemas.factura import ConfigAutonomoRead, ConfigAutonomoUpdate

router = APIRouter(prefix="/config", tags=["config"])


async def _get_or_create_config(db: DbSession, user_id: int) -> ConfigAutonomo:
    cfg = await db.scalar(select(ConfigAutonomo).where(ConfigAutonomo.user_id == user_id))
    if not cfg:
        cfg = ConfigAutonomo(user_id=user_id, metodos_cobro=["Transferencia"])
        db.add(cfg)
        await db.flush()
    return cfg


@router.get("", response_model=ConfigAutonomoRead)
async def get_config(user: CurrentUser, db: DbSession) -> ConfigAutonomoRead:
    cfg = await _get_or_create_config(db, user.id)
    await db.commit()
    return ConfigAutonomoRead.model_validate(cfg)


@router.put("", response_model=ConfigAutonomoRead)
async def update_config(payload: ConfigAutonomoUpdate, user: CurrentUser, db: DbSession) -> ConfigAutonomoRead:
    cfg = await _get_or_create_config(db, user.id)
    for k, v in payload.model_dump().items():
        setattr(cfg, k, v)
    await db.commit()
    await db.refresh(cfg)
    return ConfigAutonomoRead.model_validate(cfg)