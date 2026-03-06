from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.coleta_service import ColetaService

router = APIRouter()


class ColetaRequest(BaseModel):
    grupos: list[str] | None = None
    forcar: bool = False


@router.post("/disparar")
async def disparar_coleta(
    body: ColetaRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ColetaService()
    resultado = await service.disparar_coleta(
        grupos=body.grupos,
        forcar=body.forcar,
        db=db,
    )
    return resultado


@router.get("/status")
async def status_coleta(db: AsyncSession = Depends(get_db)):
    service = ColetaService()
    return await service.status_coleta(db=db)
