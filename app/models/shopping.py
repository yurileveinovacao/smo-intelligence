import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoShopping(str, enum.Enum):
    shopping = "shopping"
    outlet = "outlet"
    strip_mall = "strip_mall"
    outro = "outro"


class SegmentoPublico(str, enum.Enum):
    premium = "premium"
    medio_alto = "medio_alto"
    medio = "medio"
    popular = "popular"
    outlet_premium = "outlet_premium"


class Shopping(Base):
    __tablename__ = "shoppings"
    __table_args__ = {"schema": "competitive_intel"}

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(
        ForeignKey("competitive_intel.grupos.id"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_abreviado: Mapped[str | None] = mapped_column(String(60))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    tipo: Mapped[TipoShopping | None] = mapped_column(
        Enum(TipoShopping, name="tipo_shopping", schema="competitive_intel")
    )
    segmento_publico: Mapped[SegmentoPublico | None] = mapped_column(
        Enum(SegmentoPublico, name="segmento_publico", schema="competitive_intel")
    )
    abl_m2: Mapped[float | None] = mapped_column(Float)
    concorrente_direto: Mapped[bool] = mapped_column(Boolean, default=False)
    dados_individuais_ri: Mapped[bool] = mapped_column(Boolean, default=False)
    observacoes: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    grupo: Mapped["Grupo"] = relationship(back_populates="shoppings")  # noqa: F821
    resultados: Mapped[list["ResultadoTrimestral"]] = relationship(  # noqa: F821
        back_populates="shopping", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Shopping {self.nome} ({self.cidade}/{self.uf})>"
