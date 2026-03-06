from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resultado import ResultadoTrimestral
from app.models.shopping import Shopping
from app.schemas.resultado import ResultadoComparativo, ResultadoRead

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
    """Série histórica agrupada por shopping para gráficos."""
    stmt = select(Shopping).options(selectinload(Shopping.resultados))

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


@router.get("/concorrentes-rp", response_model=list[ResultadoRead])
async def concorrentes_ribeirao_preto(
    ano: int | None = Query(None),
    trimestre: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retorna resultados apenas de concorrentes diretos (Ribeirão Preto)."""
    stmt = (
        select(ResultadoTrimestral)
        .join(Shopping)
        .where(Shopping.concorrente_direto.is_(True))
    )

    if ano is not None:
        stmt = stmt.where(ResultadoTrimestral.ano == ano)
    if trimestre is not None:
        stmt = stmt.where(ResultadoTrimestral.trimestre == trimestre)

    stmt = stmt.order_by(ResultadoTrimestral.ano.desc(), ResultadoTrimestral.trimestre.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
