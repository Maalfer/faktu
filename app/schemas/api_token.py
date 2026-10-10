from datetime import datetime

from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(default="", max_length=80)


class ApiTokenRead(BaseModel):
    """Vista «segura» de un token: nunca expone el secreto."""

    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiTokenCreated(BaseModel):
    """Se devuelve SOLO al crear/regenerar: incluye el secreto en claro, una sola vez."""

    id: int
    name: str
    prefix: str
    token: str
    created_at: datetime
