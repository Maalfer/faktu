from datetime import date

from pydantic import BaseModel, Field, field_validator

# ── Tipos compartidos ────────────────────────────────────────────────────────


class TrimestreInfo(BaseModel):
    """Datos de un trimestre: número y meses que abarca."""

    num: int = Field(ge=1, le=4)
    label: str = Field(pattern=r"^T[1-4]$")
    months: str = Field(description="Meses del trimestre, p.ej. 'Ene-Mar'")


# ── Gasto ────────────────────────────────────────────────────────────────────


class GastoBase(BaseModel):
    concepto: str = Field(min_length=1, max_length=300)
    categoria: str = Field(default="Varios", max_length=40)
    fecha: date
    importe: float = Field(gt=0)
    proveedor: str = Field(default="", max_length=200)
    notas: str = Field(default="", max_length=500)

    @field_validator("concepto")
    @classmethod
    def _concepto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("el gasto necesita un concepto")
        return v


class GastoCreate(GastoBase):
    pass


class GastoUpdate(GastoBase):
    pass


class GastoRead(BaseModel):
    id: int
    concepto: str
    categoria: str
    fecha: date
    importe: float
    proveedor: str
    notas: str
    archivo: str | None = None
    trimestre: int

    model_config = {"from_attributes": True}


class GastoAnual(BaseModel):
    """Un gasto con campos necesarios para la agrupación por año/trimestre."""

    id: int
    concepto: str
    categoria: str
    fecha: date
    importe: float
    proveedor: str

    model_config = {"from_attributes": True}