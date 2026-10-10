import os
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base

CATEGORIAS_GASTO = (
    "Varios",
    "Material",
    "Transporte",
    "Hostelería",
    "Alojamiento",
    "Software",
    "Formación",
    "Mercadotecnia",
    "Hosting",
    "Suministros",
    "Asesoría",
    "Equipamiento",
    "Comisiones",
)


def _gasto_upload_path(old: str, filename: str) -> str:
    """Ruta relativa del fichero adjunto de un gasto."""
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"gastos/{uuid.uuid4().hex}{ext}"


class Gasto(Base):
    """Un gasto deducible del autónomo, agrupable por trimestre."""

    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    concepto: Mapped[str] = mapped_column(String(300))
    categoria: Mapped[str] = mapped_column(String(40), default="Varios")
    fecha: Mapped[date] = mapped_column(Date, index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    proveedor: Mapped[str] = mapped_column(String(200), default="")
    notas: Mapped[str] = mapped_column(String(500), default="")
    archivo: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ruta relativa en media/
    archivo_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)  # nombre original/legible

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="gastos")

    @property
    def trimestre(self) -> int:
        return (self.fecha.month - 1) // 3 + 1

    @property
    def archivo_url(self) -> str | None:
        if not self.archivo:
            return None
        return f"{settings.media_dir.name}/{self.archivo}"

    def __repr__(self) -> str:
        return f"<Gasto {self.concepto} {self.importe}€>"