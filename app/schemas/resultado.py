import datetime

from pydantic import BaseModel


class ResultadoRead(BaseModel):
    id: int
    shopping_id: int
    ano: int
    trimestre: int

    vendas_totais: float | None = None
    vendas_m2: float | None = None
    sss: float | None = None
    ssr: float | None = None
    taxa_ocupacao: float | None = None
    abl_propria_m2: float | None = None
    fluxo_visitantes: float | None = None
    inadimplencia_liquida: float | None = None

    receita_bruta: float | None = None
    receita_locacao: float | None = None
    noi: float | None = None
    noi_m2: float | None = None
    noi_margem: float | None = None
    ebitda_ajustado: float | None = None
    ebitda_margem: float | None = None
    ffo: float | None = None

    nivel_dado: str | None = None
    fonte: str | None = None
    url_fonte: str | None = None
    nome_arquivo_fonte: str | None = None
    notas: str | None = None
    revisado: bool

    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ResultadoComparativo(BaseModel):
    shopping_id: int
    shopping_nome: str
    grupo_nome: str
    serie: list[ResultadoRead]
