import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.downloader import ReleaseDownloader
from app.services.scraper import RIScraper

logger = logging.getLogger(__name__)


class ColetaService:
    def __init__(self):
        self.scraper = RIScraper()
        self.downloader = ReleaseDownloader()

    async def disparar_coleta(
        self,
        grupos: list[str] | None,
        forcar: bool,
        db: AsyncSession,
    ) -> dict:
        """Dispara coleta de releases para os grupos especificados."""
        if grupos is None:
            grupos = self.scraper.listar_todos_os_grupos()

        resultados: dict[str, dict] = {}
        resumo_total = {"ok": 0, "erro": 0, "ja_existe": 0, "invalido": 0, "total": 0}

        for grupo_key in grupos:
            logger.info(f"Iniciando coleta para {grupo_key}")
            resultado = self.downloader.baixar_grupo(grupo_key, forcar=forcar)
            resultados[grupo_key] = resultado

            for key in resumo_total:
                resumo_total[key] += resultado.get(key, 0)

        return {
            "grupos_processados": list(resultados.keys()),
            "detalhes": resultados,
            "resumo": resumo_total,
        }

    async def status_coleta(self, db: AsyncSession) -> dict:
        """Retorna status da última coleta e cobertura por grupo."""
        relatorio = self.downloader.manifesto.relatorio()

        # Agrupa por grupo
        cobertura: dict[str, dict] = {}
        for download in relatorio["downloads"]:
            grupo = download.get("grupo", "desconhecido")
            if grupo not in cobertura:
                cobertura[grupo] = {"ok": 0, "erro": 0, "total": 0, "trimestres": []}
            cobertura[grupo]["total"] += 1
            if download["status"] == "ok":
                cobertura[grupo]["ok"] += 1
                tri = f"{download.get('trimestre')}T{download.get('ano')}"
                cobertura[grupo]["trimestres"].append(tri)
            elif download["status"] == "erro":
                cobertura[grupo]["erro"] += 1

        return {
            "total_downloads": relatorio["total"],
            "resumo": {
                "ok": relatorio["ok"],
                "erro": relatorio["erro"],
                "ja_existe": relatorio["ja_existe"],
                "invalido": relatorio["invalido"],
            },
            "cobertura_por_grupo": cobertura,
        }
