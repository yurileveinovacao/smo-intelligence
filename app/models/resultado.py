import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NivelDado(str, enum.Enum):
    individual = "individual"
    grupo = "grupo"
    estimativa = "estimativa"


class ResultadoTrimestral(Base):
    __tablename__ = "resultados_trimestrais"
    __table_args__ = (
        UniqueConstraint("shopping_id", "ano", "trimestre", name="uq_shopping_ano_tri"),
        {"schema": "competitive_intel"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shopping_id: Mapped[int] = mapped_column(
        ForeignKey("competitive_intel.shoppings.id"), nullable=False
    )
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    trimestre: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Metricas operacionais
    vendas_totais: Mapped[float | None] = mapped_column(Float)
    vendas_m2: Mapped[float | None] = mapped_column(Float)
    sss: Mapped[float | None] = mapped_column(Float)
    ssr: Mapped[float | None] = mapped_column(Float)
    taxa_ocupacao: Mapped[float | None] = mapped_column(Float)
    abl_propria_m2: Mapped[float | None] = mapped_column(Float)
    fluxo_visitantes: Mapped[float | None] = mapped_column(Float)
    inadimplencia_liquida: Mapped[float | None] = mapped_column(Float)

    # Metricas financeiras
    receita_bruta: Mapped[float | None] = mapped_column(Float)
    receita_locacao: Mapped[float | None] = mapped_column(Float)
    noi: Mapped[float | None] = mapped_column(Float)
    noi_m2: Mapped[float | None] = mapped_column(Float)
    noi_margem: Mapped[float | None] = mapped_column(Float)
    ebitda_ajustado: Mapped[float | None] = mapped_column(Float)
    ebitda_margem: Mapped[float | None] = mapped_column(Float)
    ffo: Mapped[float | None] = mapped_column(Float)

    # Metadados
    nivel_dado: Mapped[NivelDado | None] = mapped_column(
        Enum(NivelDado, name="nivel_dado", schema="competitive_intel")
    )
    fonte: Mapped[str | None] = mapped_column(String(200))
    url_fonte: Mapped[str | None] = mapped_column(String(500))
    nome_arquivo_fonte: Mapped[str | None] = mapped_column(String(300))
    notas: Mapped[str | None] = mapped_column(Text)
    revisado: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shopping: Mapped["Shopping"] = relationship(back_populates="resultados")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Resultado {self.shopping_id} {self.trimestre}T{self.ano}>"
