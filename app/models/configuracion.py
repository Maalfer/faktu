from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConfigAutonomo(Base):
    """Datos de facturación del usuario + preferencias por defecto."""

    __tablename__ = "config_autonomo"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    emisor_nombre: Mapped[str] = mapped_column(String(200), default="")
    emisor_nif: Mapped[str] = mapped_column(String(30), default="")
    emisor_direccion: Mapped[str] = mapped_column(String(300), default="")
    emisor_cp: Mapped[str] = mapped_column(String(10), default="")
    emisor_ciudad: Mapped[str] = mapped_column(String(100), default="")
    emisor_provincia: Mapped[str] = mapped_column(String(100), default="")
    emisor_pais: Mapped[str] = mapped_column(String(100), default="España")
    emisor_email: Mapped[str] = mapped_column(String(200), default="")
    emisor_telefono: Mapped[str] = mapped_column(String(30), default="")
    serie_por_defecto: Mapped[str] = mapped_column(String(20), default="")
    iva_por_defecto: Mapped[float] = mapped_column(default=21.0)
    irpf_por_defecto: Mapped[float] = mapped_column(default=0.0)
    metodos_cobro: Mapped[list[Any]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="config")

    def __repr__(self) -> str:
        return f"<ConfigAutonomo {self.user_id}>"