import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.downloader import ReleaseDownloader
from app.services.extractor import extrair_metricas_pdf, salvar_resultado
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
        """Dispara coleta de releases: download → extração → persistência."""
        if grupos is None:
            grupos = self.scraper.listar_todos_os_grupos()

        resultados: dict[str, dict] = {}
        resumo_total = {
            "ok": 0, "erro": 0, "ja_existe": 0, "invalido": 0, "total": 0,
            "extraidos": 0, "salvos": 0,
        }

        for grupo_key in grupos:
            logger.info(f"Iniciando coleta para {grupo_key}")
            resultado_grupo = self._coletar_grupo(grupo_key, forcar=forcar)

            # Extrai métricas e salva no banco para cada PDF baixado com sucesso
            extraidos = 0
            salvos = 0
            for download in resultado_grupo.get("downloads_ok", []):
                caminho = download.get("caminho")
                ano = download.get("ano")
                trimestre = download.get("trimestre")

                if not caminho or not ano or not trimestre:
                    continue

                try:
                    metrics = extrair_metricas_pdf(caminho, grupo_key, ano, trimestre)
                    if metrics:
                        extraidos += 1
                        registro = await salvar_resultado(
                            db=db,
                            grupo_key=grupo_key,
                            ano=ano,
                            trimestre=trimestre,
                            metrics=metrics,
                            fonte="release_pdf",
                            url_fonte=download.get("url"),
                            nome_arquivo=download.get("nome_arquivo"),
                        )
                        if registro:
                            salvos += 1
                except Exception as e:
                    logger.error(
                        "Falha na extração/persistência de %s %dT%d: %s",
                        grupo_key, trimestre, ano, e,
                    )

            if salvos > 0:
                await db.commit()

            resultado_grupo["extraidos"] = extraidos
            resultado_grupo["salvos"] = salvos
            resultados[grupo_key] = resultado_grupo

            for key in ("ok", "erro", "ja_existe", "invalido", "total"):
                resumo_total[key] += resultado_grupo.get(key, 0)
            resumo_total["extraidos"] += extraidos
            resumo_total["salvos"] += salvos

        return {
            "grupos_processados": list(resultados.keys()),
            "detalhes": resultados,
            "resumo": resumo_total,
        }

    def _coletar_grupo(self, grupo_key: str, forcar: bool = False) -> dict:
        """Baixa todos os releases de um grupo e retorna detalhes dos downloads."""
        releases = self.scraper.descobrir_releases(grupo_key)
        logger.info(f"Encontrados {len(releases)} releases para {grupo_key}")

        resultado = {
            "ok": 0, "erro": 0, "ja_existe": 0, "invalido": 0,
            "total": len(releases), "downloads_ok": [],
        }

        for release in releases:
            download = self.downloader.baixar(release, forcar=forcar)
            status = download["status"]
            resultado[status] = resultado.get(status, 0) + 1

            # Registra downloads bem-sucedidos para extração posterior
            if status in ("ok", "ja_existe"):
                resultado["downloads_ok"].append({
                    "caminho": download.get("caminho"),
                    "url": release.get("url"),
                    "nome_arquivo": release.get("nome_arquivo"),
                    "ano": release.get("ano"),
                    "trimestre": release.get("trimestre"),
                    "grupo": grupo_key,
                })

            time.sleep(settings.HTTP_DELAY)

        return resultado

    async def status_coleta(self, db: AsyncSession) -> dict:
        """Retorna status da última coleta e cobertura por grupo."""
        relatorio = self.downloader.manifesto.relatorio()

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
