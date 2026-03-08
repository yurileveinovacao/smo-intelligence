import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"SMO Intelligence starting ({settings.ENVIRONMENT})")
    logger.info(f"PORT={os.environ.get('PORT', '(not set, default 8080)')}")

    # Log mascarado da URL do banco
    db_url = settings.effective_database_url
    if "@" in db_url:
        masked = db_url.split("@")[0][:20] + "***@" + db_url.split("@")[1]
    else:
        masked = db_url[:30] + "..."
    logger.info(f"DATABASE_URL={masked}")

    try:
        settings.RELEASES_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"RELEASES_DIR={settings.RELEASES_DIR} (ok)")
    except Exception as e:
        logger.warning(f"Nao conseguiu criar RELEASES_DIR: {e}")

    logger.info("Startup completo — pronto para receber requests")
    logger.info("=" * 60)
    yield
    logger.info("SMO Intelligence shutting down")


app = FastAPI(
    title="SMO Intelligence",
    description="Sistema de inteligência competitiva — Santa Maria Outlet",
    version="0.1.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "https://admin.santamariaoutlet.com.br",   # painel admin producao
    "https://smo.leveinovacao.com.br",          # dominio Leve
    "http://34.151.247.17",                     # IP VM smo-analise-vm (fallback)
    "http://34.151.243.151",                    # IP VM servidor-smo-vpn (fallback)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }
