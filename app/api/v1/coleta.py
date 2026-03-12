from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.coleta_service import ColetaService
from app.services.extractor import carregar_jsons_existentes

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


@router.post("/carregar-jsons")
async def carregar_jsons(db: AsyncSession = Depends(get_db)):
    """Carrega os JSONs já extraídos (docs/extracted/) para o banco.

    Útil para popular dados históricos sem re-baixar/re-extrair PDFs.
    """
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    extracted_dir = str(project_root / "docs" / "extracted")
    resultado = await carregar_jsons_existentes(db, extracted_dir)
    return resultado
