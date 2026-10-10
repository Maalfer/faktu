from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TipoConcepto = Literal["ingreso", "gasto"]


class ConceptoBase(BaseModel):
    year: int = Field(ge=2000, le=2100)
    trimestre: int = Field(ge=1, le=4)
    tipo: TipoConcepto
    concepto: str = Field(min_length=1, max_length=300)
    importe: Decimal = Field(gt=0)
    iva: Decimal | None = Field(default=None, ge=0, le=100)
    orden: int = 0
    notas: str = Field(default="", max_length=500)

    @field_validator("concepto")
    @classmethod
    def _concepto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("el concepto no puede estar vacío")
        return v


class ConceptoCreate(ConceptoBase):
    pass


class ConceptoUpdate(ConceptoBase):
    pass


class ConceptoRead(ConceptoBase):
    """``auto=True``: fila calculada desde una factura (Ingresos) o un gasto; no se edita aquí."""

    id: int | None = None
    auto: bool = False
    origen: Literal["manual", "factura", "gasto"] = "manual"
    ref_id: int | None = None

    model_config = {"from_attributes": True}


class QuarterConceptos(BaseModel):
    """Conceptos de ingreso y gasto de un trimestre, con sus totales."""

    num: int
    label: str
    months: str
    is_current: bool
    is_future: bool
    is_past: bool
    ingresos: list[ConceptoRead]
    gastos: list[ConceptoRead]
    total_ingresos: Decimal
    total_gastos: Decimal
    neto: Decimal


class ConceptosResponse(BaseModel):
    year: int
    current_year: int
    current_quarter: int
    years: list[int]
    trimestres: list[QuarterConceptos]
    total_ingresos: Decimal
    total_gastos: Decimal
    total_neto: Decimal
