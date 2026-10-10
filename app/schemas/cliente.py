from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def _check_nombre(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("este campo es obligatorio")
    return v


class ClienteBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    nif: str = Field(default="", max_length=30)
    direccion: str = Field(default="", max_length=300)
    cp: str = Field(default="", max_length=10)
    ciudad: str = Field(default="", max_length=100)
    provincia: str = Field(default="", max_length=100)
    pais: str = Field(default="España", max_length=100)
    email: str = Field(default="", max_length=200)
    telefono: str = Field(default="", max_length=30)
    notas: str = Field(default="", max_length=500)

    _nombre = field_validator("nombre")(_check_nombre)


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class ClienteRead(ClienteBase):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}