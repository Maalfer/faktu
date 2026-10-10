from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ESTADO_CHOICES = ("borrador", "emitida", "pagada")


class Factura(Base):
    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )

    numero: Mapped[str] = mapped_column(String(50))  # p.ej. "3/2026"
    serie: Mapped[str] = mapped_column(String(20), default="")
    fecha_emision: Mapped[date] = mapped_column(Date, index=True)

    # Emisor (datos de facturación del autónomo)
    emisor_nombre: Mapped[str] = mapped_column(String(200))
    emisor_nif: Mapped[str] = mapped_column(String(30))
    emisor_direccion: Mapped[str] = mapped_column(String(300), default="")
    emisor_cp: Mapped[str] = mapped_column(String(10), default="")
    emisor_ciudad: Mapped[str] = mapped_column(String(100), default="")
    emisor_provincia: Mapped[str] = mapped_column(String(100), default="")
    emisor_pais: Mapped[str] = mapped_column(String(100), default="España")
    emisor_email: Mapped[str] = mapped_column(String(200), default="")
    emisor_telefono: Mapped[str] = mapped_column(String(30), default="")

    # Receptor
    receptor_nombre: Mapped[str] = mapped_column(String(200))
    receptor_nif: Mapped[str] = mapped_column(String(30), default="")
    receptor_direccion: Mapped[str] = mapped_column(String(300), default="")
    receptor_cp: Mapped[str] = mapped_column(String(10), default="")
    receptor_ciudad: Mapped[str] = mapped_column(String(100), default="")
    receptor_provincia: Mapped[str] = mapped_column(String(100), default="")
    receptor_pais: Mapped[str] = mapped_column(String(100), default="España")

    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("21"))
    irpf_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(20), default="emitida")
    metodo_cobro: Mapped[str] = mapped_column(String(40), default="")
    notas: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="facturas")
    cliente = relationship("Cliente", back_populates="facturas")
    lineas = relationship(
        "LineaFactura",
        back_populates="factura",
        cascade="all, delete-orphan",
        order_by="LineaFactura.orden",
    )

    # ── Cálculos ────────────────────────────────────────────────────────────
    @property
    def base_imponible(self) -> Decimal:
        return sum((l.importe for l in self.lineas), Decimal("0"))

    @property
    def cuota_iva(self) -> Decimal:
        return (self.base_imponible * self.iva_porcentaje / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def cuota_irpf(self) -> Decimal:
        return (self.base_imponible * self.irpf_porcentaje / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return self.base_imponible + self.cuota_iva - self.cuota_irpf

    @property
    def numero_completo(self) -> str:
        return f"{self.serie}{self.numero}" if self.serie else self.numero

    @property
    def trimestre(self) -> int:
        return (self.fecha_emision.month - 1) // 3 + 1

    def __repr__(self) -> str:
        return f"<Factura {self.numero_completo}>"


class LineaFactura(Base):
    __tablename__ = "lineas_factura"

    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id", ondelete="CASCADE"), index=True)
    concepto: Mapped[str] = mapped_column(String(400))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1"))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    orden: Mapped[int] = mapped_column(Integer, default=0)

    factura = relationship("Factura", back_populates="lineas")

    @property
    def importe(self) -> Decimal:
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return f"<Linea {self.concepto} {self.importe}€>"