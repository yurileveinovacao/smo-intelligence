from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.grupo import Grupo
from app.schemas.grupo import GrupoDetail, GrupoRead

router = APIRouter()


@router.get("", response_model=list[GrupoRead])
async def listar_grupos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Grupo).where(Grupo.ativo.is_(True)).order_by(Grupo.nome)
    )
    return result.scalars().all()


@router.get("/{grupo_id}", response_model=GrupoDetail)
async def detalhe_grupo(grupo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Grupo).where(Grupo.id == grupo_id))
    grupo = result.scalar_one_or_none()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    return grupo
