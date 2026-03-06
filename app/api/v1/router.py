from fastapi import APIRouter

from app.api.v1.grupos import router as grupos_router
from app.api.v1.shoppings import router as shoppings_router
from app.api.v1.resultados import router as resultados_router
from app.api.v1.coleta import router as coleta_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(grupos_router, prefix="/grupos", tags=["Grupos"])
api_router.include_router(shoppings_router, prefix="/shoppings", tags=["Shoppings"])
api_router.include_router(resultados_router, prefix="/resultados", tags=["Resultados"])
api_router.include_router(coleta_router, prefix="/coleta", tags=["Coleta"])
