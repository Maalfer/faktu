from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

TIPOS_CONCEPTO = ("ingreso", "gasto")


class ConceptoTrimestre(Base):
    """Un concepto de ingreso o gasto agrupado por trimestre.

    Es un libro independiente del de facturas/gastos: el autónomo anota aquí,
    a mano, los conceptos con los que resume cada trimestre (como en su Excel).
    """

    __tablename__ = "conceptos_trimestre"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    year: Mapped[int] = mapped_column(Integer, index=True)
    trimestre: Mapped[int] = mapped_column(Integer)  # 1..4
    tipo: Mapped[str] = mapped_column(String(10))  # "ingreso" | "gasto"
    concepto: Mapped[str] = mapped_column(String(300))
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # IVA como porcentaje (21.00 = 21 %). None equivale a "N/A" (p.ej. operaciones exentas).
    iva: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    notas: Mapped[str] = mapped_column(String(500), default="")
    # Origen automático (botón «Generar desde facturas y gastos»); None = anotado a mano.
    factura_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    gasto_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="conceptos")

    def __repr__(self) -> str:
        return f"<ConceptoTrimestre {self.tipo} {self.concepto} {self.importe}€>"
