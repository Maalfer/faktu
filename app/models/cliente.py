from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Cliente(Base):
    """Cliente o receptor de facturas de un usuario."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    nombre: Mapped[str] = mapped_column(String(200))
    nif: Mapped[str] = mapped_column(String(30), default="", index=True)
    direccion: Mapped[str] = mapped_column(String(300), default="")
    cp: Mapped[str] = mapped_column(String(10), default="")
    ciudad: Mapped[str] = mapped_column(String(100), default="")
    provincia: Mapped[str] = mapped_column(String(100), default="")
    pais: Mapped[str] = mapped_column(String(100), default="España")
    email: Mapped[str] = mapped_column(String(200), default="")
    telefono: Mapped[str] = mapped_column(String(30), default="")
    notas: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="clientes")
    facturas = relationship("Factura", back_populates="cliente")

    def __repr__(self) -> str:
        return f"<Cliente {self.id} {self.nombre}>"