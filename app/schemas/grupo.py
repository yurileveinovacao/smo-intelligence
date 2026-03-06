import datetime

from pydantic import BaseModel


class GrupoRead(BaseModel):
    id: int
    nome: str
    ticker: str | None = None
    url_ri: str | None = None
    capital_aberto: bool
    ativo: bool
    observacoes: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ShoppingBrief(BaseModel):
    id: int
    nome: str
    cidade: str | None = None
    uf: str | None = None
    concorrente_direto: bool

    model_config = {"from_attributes": True}


class GrupoDetail(GrupoRead):
    shoppings: list[ShoppingBrief] = []
