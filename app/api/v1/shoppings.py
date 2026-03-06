from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.shopping import Shopping
from app.schemas.shopping import ShoppingDetail, ShoppingRead

router = APIRouter()


@router.get("", response_model=list[ShoppingRead])
async def listar_shoppings(
    grupo_id: int | None = Query(None),
    concorrente_direto: bool | None = Query(None),
    cidade: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Shopping).where(Shopping.ativo.is_(True))

    if grupo_id is not None:
        stmt = stmt.where(Shopping.grupo_id == grupo_id)
    if concorrente_direto is not None:
        stmt = stmt.where(Shopping.concorrente_direto == concorrente_direto)
    if cidade is not None:
        stmt = stmt.where(Shopping.cidade.ilike(f"%{cidade}%"))

    stmt = stmt.order_by(Shopping.nome)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{shopping_id}", response_model=ShoppingDetail)
async def detalhe_shopping(shopping_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shopping).where(Shopping.id == shopping_id))
    shopping = result.scalar_one_or_none()
    if not shopping:
        raise HTTPException(status_code=404, detail="Shopping não encontrado")
    return shopping
