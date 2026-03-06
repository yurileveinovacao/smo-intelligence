import datetime

from pydantic import BaseModel


class ShoppingRead(BaseModel):
    id: int
    grupo_id: int
    nome: str
    nome_abreviado: str | None = None
    cidade: str | None = None
    uf: str | None = None
    tipo: str | None = None
    segmento_publico: str | None = None
    abl_m2: float | None = None
    concorrente_direto: bool
    dados_individuais_ri: bool
    observacoes: str | None = None
    ativo: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ResultadoBrief(BaseModel):
    id: int
    ano: int
    trimestre: int
    vendas_totais: float | None = None
    taxa_ocupacao: float | None = None
    noi: float | None = None

    model_config = {"from_attributes": True}


class ShoppingDetail(ShoppingRead):
    resultados: list[ResultadoBrief] = []
