import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Grupo(Base):
    __tablename__ = "grupos"
    __table_args__ = {"schema": "competitive_intel"}

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(10))
    url_ri: Mapped[str | None] = mapped_column(String(300))
    capital_aberto: Mapped[bool] = mapped_column(Boolean, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shoppings: Mapped[list["Shopping"]] = relationship(  # noqa: F821
        back_populates="grupo", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Grupo {self.nome} ({self.ticker})>"
