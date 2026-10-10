from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.cliente import ClienteRead

EstadoFactura = Literal["borrador", "emitida", "pagada"]


def _check_nombre(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("este campo es obligatorio")
    return v


class LineaFacturaCreate(BaseModel):
    concepto: str = Field(min_length=1, max_length=400)
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio_unitario: Decimal = Field(gt=0)
    orden: int = Field(default=0, ge=0)

    @field_validator("concepto")
    @classmethod
    def _concepto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("la línea necesita un concepto")
        return v


class LineaFacturaRead(LineaFacturaCreate):
    id: int
    importe: Decimal

    model_config = {"from_attributes": True}


class FacturaBase(BaseModel):
    numero: str = Field(min_length=1, max_length=50)
    serie: str = Field(default="", max_length=20)
    fecha_emision: date
    cliente_id: int | None = None
    # True: ingreso sin factura a un cliente; receptor_nombre es el origen (Skool, Academia…)
    sin_cliente: bool = False

    emisor_nombre: str = Field(min_length=1, max_length=200)
    emisor_nif: str = Field(min_length=1, max_length=30)
    emisor_direccion: str = Field(default="", max_length=300)
    emisor_cp: str = Field(default="", max_length=10)
    emisor_ciudad: str = Field(default="", max_length=100)
    emisor_provincia: str = Field(default="", max_length=100)
    emisor_pais: str = Field(default="España", max_length=100)
    emisor_email: str = Field(default="", max_length=200)
    emisor_telefono: str = Field(default="", max_length=30)

    receptor_nombre: str = Field(min_length=1, max_length=200)
    receptor_nif: str = Field(default="", max_length=30)
    receptor_direccion: str = Field(default="", max_length=300)
    receptor_cp: str = Field(default="", max_length=10)
    receptor_ciudad: str = Field(default="", max_length=100)
    receptor_provincia: str = Field(default="", max_length=100)
    receptor_pais: str = Field(default="España", max_length=100)

    iva_porcentaje: Decimal = Field(default=Decimal("21"), ge=0, le=100)
    irpf_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    estado: EstadoFactura = "emitida"
    metodo_cobro: str = Field(default="", max_length=40)
    notas: str = Field(default="", max_length=5000)
    lineas: list[LineaFacturaCreate] = Field(default_factory=list, min_length=0)

    _emisor = field_validator("emisor_nombre", "emisor_nif")(_check_nombre)
    _receptor = field_validator("receptor_nombre")(_check_nombre)

    @model_validator(mode="after")
    def _sin_cliente(self):
        """Un ingreso sin cliente no lleva datos fiscales del receptor ni cliente vinculado."""
        if self.sin_cliente:
            self.cliente_id = None
            self.irpf_porcentaje = Decimal("0")
            for campo in ("nif", "direccion", "cp", "ciudad", "provincia"):
                setattr(self, f"receptor_{campo}", "")
        return self


class FacturaCreate(FacturaBase):
    pass


class FacturaUpdate(FacturaBase):
    pass


class FacturaRead(BaseModel):
    id: int
    numero: str
    serie: str
    numero_completo: str
    sin_cliente: bool = False
    fecha_emision: date
    estado: EstadoFactura
    cliente_id: int | None
    cliente: ClienteRead | None = None
    receptor_nombre: str
    iva_porcentaje: Decimal
    irpf_porcentaje: Decimal
    base_imponible: Decimal
    cuota_iva: Decimal
    cuota_irpf: Decimal
    total: Decimal
    trimestre: int
    metodo_cobro: str
    notas: str
    lineas: list[LineaFacturaRead]

    model_config = {"from_attributes": True}


class FacturaListItem(BaseModel):
    """Resumen compacto para listas y agrupación por trimestres."""

    id: int
    numero_completo: str
    numero: str
    serie: str
    sin_cliente: bool = False
    fecha_emision: date
    estado: EstadoFactura
    receptor_nombre: str
    base_imponible: Decimal
    cuota_iva: Decimal
    total: Decimal

    model_config = {"from_attributes": True}


class NextNumeroResponse(BaseModel):
    numero: str
    serie: str


class ConfigAutonomoRead(BaseModel):
    """Configuración del autónomo (también usada para precargar datos al crear)."""

    emisor_nombre: str
    emisor_nif: str
    emisor_direccion: str
    emisor_cp: str
    emisor_ciudad: str
    emisor_provincia: str
    emisor_pais: str
    emisor_email: str
    emisor_telefono: str
    serie_por_defecto: str
    iva_por_defecto: float
    irpf_por_defecto: float
    metodos_cobro: list[str]

    model_config = {"from_attributes": True}


class ConfigAutonomoUpdate(BaseModel):
    emisor_nombre: str = ""
    emisor_nif: str = ""
    emisor_direccion: str = ""
    emisor_cp: str = ""
    emisor_ciudad: str = ""
    emisor_provincia: str = ""
    emisor_pais: str = "España"
    emisor_email: str = ""
    emisor_telefono: str = ""
    serie_por_defecto: str = ""
    iva_por_defecto: float = 21.0
    irpf_por_defecto: float = 0.0
    metodos_cobro: list[str] = []