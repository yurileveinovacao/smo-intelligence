from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resultado import ResultadoTrimestral
from app.models.shopping import Shopping
from app.schemas.resultado import (
    ResultadoComparativo,
    ResultadoDetalhado,
    ResultadoRead,
)

router = APIRouter()


@router.get("", response_model=list[ResultadoRead])
async def listar_resultados(
    shopping_id: int | None = Query(None),
    ano: int | None = Query(None),
    trimestre: int | None = Query(None),
    grupo_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ResultadoTrimestral)

    if shopping_id is not None:
        stmt = stmt.where(ResultadoTrimestral.shopping_id == shopping_id)
    if ano is not None:
        stmt = stmt.where(ResultadoTrimestral.ano == ano)
    if trimestre is not None:
        stmt = stmt.where(ResultadoTrimestral.trimestre == trimestre)
    if grupo_id is not None:
        stmt = stmt.join(Shopping).where(Shopping.grupo_id == grupo_id)

    stmt = stmt.order_by(ResultadoTrimestral.ano.desc(), ResultadoTrimestral.trimestre.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/comparativo", response_model=list[ResultadoComparativo])
async def comparativo(
    ano: int | None = Query(None),
    grupo_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Serie historica agrupada por shopping para graficos."""
    stmt = select(Shopping).options(
        selectinload(Shopping.resultados),
        selectinload(Shopping.grupo),
    )

    if grupo_id is not None:
        stmt = stmt.where(Shopping.grupo_id == grupo_id)

    stmt = stmt.where(Shopping.ativo.is_(True))
    result = await db.execute(stmt)
    shoppings = result.scalars().all()

    comparativos = []
    for shopping in shoppings:
        resultados = shopping.resultados
        if ano is not None:
            resultados = [r for r in resultados if r.ano == ano]
        if not resultados:
            continue
        resultados.sort(key=lambda r: (r.ano, r.trimestre))

        comparativos.append(
            ResultadoComparativo(
                shopping_id=shopping.id,
                shopping_nome=shopping.nome,
                grupo_nome=shopping.grupo.nome if shopping.grupo else "N/A",
                serie=[ResultadoRead.model_validate(r) for r in resultados],
            )
        )

    return comparativos


@router.get("/concorrentes-rp", response_model=list[ResultadoDetalhado])
async def concorrentes_ribeirao_preto(
    ano: int | None = Query(None),
    trimestre: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retorna resultados de todos os shoppings ativos com info de shopping e grupo.

    Inclui shopping_nome, grupo_nome e abl_m2 em cada resultado para o dashboard.
    """
    stmt = (
        select(ResultadoTrimestral, Shopping)
        .join(Shopping)
        .options(selectinload(Shopping.grupo))
        .where(Shopping.ativo.is_(True))
    )

    if ano is not None:
        stmt = stmt.where(ResultadoTrimestral.ano == ano)
    if trimestre is not None:
        stmt = stmt.where(ResultadoTrimestral.trimestre == trimestre)

    stmt = stmt.order_by(
        ResultadoTrimestral.ano.desc(),
        ResultadoTrimestral.trimestre.desc(),
        Shopping.nome,
    )
    result = await db.execute(stmt)
    rows = result.all()

    detalhados = []
    for resultado, shopping in rows:
        detalhados.append(
            ResultadoDetalhado(
                id=resultado.id,
                shopping_id=resultado.shopping_id,
                shopping_nome=shopping.nome,
                grupo_nome=shopping.grupo.nome if shopping.grupo else "N/A",
                abl_m2=shopping.abl_m2,
                ano=resultado.ano,
                trimestre=resultado.trimestre,
                vendas_totais=resultado.vendas_totais,
                vendas_m2=resultado.vendas_m2,
                sss=resultado.sss,
                ssr=resultado.ssr,
                taxa_ocupacao=resultado.taxa_ocupacao,
                abl_propria_m2=resultado.abl_propria_m2,
                fluxo_visitantes=resultado.fluxo_visitantes,
                inadimplencia_liquida=resultado.inadimplencia_liquida,
                receita_bruta=resultado.receita_bruta,
                receita_locacao=resultado.receita_locacao,
                noi=resultado.noi,
                noi_m2=resultado.noi_m2,
                noi_margem=resultado.noi_margem,
                ebitda_ajustado=resultado.ebitda_ajustado,
                ebitda_margem=resultado.ebitda_margem,
                ffo=resultado.ffo,
                nivel_dado=resultado.nivel_dado.value if resultado.nivel_dado else None,
                fonte=resultado.fonte,
                revisado=resultado.revisado,
            )
        )

    return detalhados
