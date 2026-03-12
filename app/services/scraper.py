import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Regex para extrair trimestre/ano: 1T23, 2T2023, 3Q24, etc.
TRI_ANO_RE = re.compile(r"([1-4])\s*[TtQq]\s*(\d{2,4})", re.IGNORECASE)

# ─── API MZ Group ────────────────────────────────────────────────────────────
# Multiplan e Allos usam a plataforma MZ Group (mziq.com) para hospedar
# documentos de RI. A API é pública e retorna URLs diretas dos PDFs.

MZ_API_BASE = "https://apicatalog.mziq.com/filemanager"

MZ_COMPANIES: dict[str, dict] = {
    "multiplan": {
        "company_id": "08dd2899-a019-4531-a90c-f00c9f91b0ff",
        "category": "releases-de-resultados",
    },
    "allos": {
        "company_id": "330c258b-6212-45ce-8c13-557ea46cc23a",
        "category": "release-resultados",
    },
}


def _buscar_releases_mz(grupo_key: str, anos: list[int] | None = None) -> list[dict]:
    """Busca releases via API MZ Group (Multiplan, Allos).

    A API retorna metadados dos documentos incluindo URL direta do PDF,
    trimestre, ano e título.
    """
    config = MZ_COMPANIES.get(grupo_key)
    if not config:
        return []

    if anos is None:
        from datetime import datetime
        ano_atual = datetime.now().year
        anos = list(range(2023, ano_atual + 1))

    releases: list[dict] = []
    url = f"{MZ_API_BASE}/company/{config['company_id']}/filter/categories/year/meta"

    for ano in anos:
        try:
            resp = requests.post(
                url,
                json={
                    "year": ano,
                    "categories": [config["category"]],
                    "language": "pt_BR",
                    "published": True,
                },
                headers={"Content-Type": "application/json"},
                timeout=settings.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            for doc in data.get("data", {}).get("document_metas", []):
                file_url = doc.get("file_url") or doc.get("permalink", "")
                trimestre = doc.get("file_quarter")
                file_year = doc.get("file_year", ano)

                if not file_url or not trimestre:
                    continue

                releases.append({
                    "url": file_url,
                    "nome_arquivo": f"{grupo_key}_{trimestre}T{file_year}_release.pdf",
                    "ano": file_year,
                    "trimestre": trimestre,
                    "tipo": "pdf",
                    "fonte": "api_mz",
                    "grupo": grupo_key,
                })

            logger.info(
                "API MZ %s/%d -> %d releases",
                grupo_key, ano,
                len([r for r in releases if r["ano"] == ano]),
            )

        except Exception as e:
            logger.warning("Falha na API MZ para %s/%d: %s", grupo_key, ano, e)

    return releases


class RIScraper:
    GRUPOS_CONFIG: dict[str, dict] = {
        "multiplan": {
            "nome": "Multiplan",
            "ticker": "MULT3",
            "ri_url": "https://ri.multiplan.com.br",
            "releases_url": "https://ri.multiplan.com.br/ferramentas-de-analise/central-de-resultados/",
            "metodo": "api_mz",
            "keywords": ["resultado", "release", "trimestre", "quarterly", "suplemento"],
            "extensoes": [".pdf", ".xlsx"],
        },
        "iguatemi": {
            "nome": "Iguatemi S.A.",
            "ticker": "IGTI11",
            "ri_url": "https://ri.iguatemi.com.br",
            "releases_url": "https://ri.iguatemi.com.br/central-de-resultados",
            "metodo": "scraping_html",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
        "allos": {
            "nome": "Allos",
            "ticker": "ALOS3",
            "ri_url": "https://ri.allos.com.br",
            "releases_url": "https://ri.allos.com.br/informacoes-financeiras/central-de-resultados/",
            "metodo": "api_mz",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
        "general_shopping": {
            "nome": "General Shopping",
            "ticker": "GSHP3",
            "ri_url": "https://ri.generalshopping.com.br",
            "releases_url": "https://ri.generalshopping.com.br/listresultados.aspx?idCanal=3e+m1FdNEdVcLHmdXh6lUg==",
            "metodo": "scraping_html",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
    }

    # URLs com hash codificado para Iguatemi e General Shopping
    # Esses sites usam Download.aspx?Arquivo=<hash> onde o hash muda por documento
    RELEASES_CONHECIDOS: dict[str, list[dict]] = {
        "multiplan": [
            # 2023
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/7a5795c0-5f7c-6070-9ab4-dc1ac9e9352a?origin=2", "ano": 2023, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/cff1ee37-c346-fb40-502f-d571f445d393?origin=2", "ano": 2023, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/d0a5ed15-ac95-ea8b-45f4-7a3fc3276320?origin=2", "ano": 2023, "trimestre": 3},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/9ff0ff14-8949-0be1-22a8-71cf8e942269?origin=2", "ano": 2023, "trimestre": 4},
            # 2024
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/a09a4f87-736f-4c8f-e1d4-20d2959d9c07?origin=2", "ano": 2024, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/1ce48426-24f1-def2-c2c4-c064c015da3a?origin=2", "ano": 2024, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/8d51c04c-efc2-6e9d-1047-1e73b5337f1c?origin=2", "ano": 2024, "trimestre": 3},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/979d32d8-8e9c-cb60-a205-ef4cc0adf93b?origin=2", "ano": 2024, "trimestre": 4},
            # 2025
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/25380c81-51e5-0bc5-4092-69ac80eaba4c?origin=2", "ano": 2025, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/dc28f0dd-f29c-bbb4-5f6c-0d8a19ffa29b?origin=2", "ano": 2025, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/08dd2899-a019-4531-a90c-f00c9f91b0ff/0e94c5ce-9160-e915-1c5f-34e7a55dd28a?origin=2", "ano": 2025, "trimestre": 3},
            {"url": "https://filemanager-cdn.mziq.com/published/08dd2899-a019-4531-a90c-f00c9f91b0ff/bb89f00d-f80c-4db6-b698-6e8904ba1532_er_4q25_port.pdf", "ano": 2025, "trimestre": 4},
        ],
        "iguatemi": [
            # 2023 — Relatório de Resultados (PDF)
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=RVhwDtstUbbRG9YoQ4oyTA==", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=kZ6OfOwWDyDqR1l5g7nLIA==", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=1aeVqlS6OmjE//C1LaGiHg==", "ano": 2025, "trimestre": 3},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=E30o1WVrpIDxfzYOKdla+Q==", "ano": 2025, "trimestre": 4},
            # 2024
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=Uz/pMWaZvX1NdKs/UQTn9A==", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=zRqfwWxVnk8zzJvUiLS1FA==", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=sFTl0Y50cjs6n0oNPNbacA==", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=r+VDBESEVvmYCmR58Kp3jg==", "ano": 2024, "trimestre": 4},
        ],
        "allos": [
            # 2023
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/d371275d-f278-a4a3-e9a3-1c0b234d1c1f?origin=2", "ano": 2023, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/ec1e8726-297e-1ca2-f580-a9574be3702a?origin=2", "ano": 2023, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/e6800ba3-f153-9883-0429-908722e61625?origin=2", "ano": 2023, "trimestre": 3},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/2fa2c725-62de-5a3c-fb7f-bcb9b9095687?origin=2", "ano": 2023, "trimestre": 4},
            # 2024
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/19bcb6b1-920b-bfeb-cf3a-4257bdae5f77?origin=2", "ano": 2024, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/30311ce6-96c0-4e55-38e0-825d9184e999?origin=2", "ano": 2024, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/2a8a23be-8b88-42f9-9e70-48511cc1ae5d?origin=2", "ano": 2024, "trimestre": 3},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/045b8af2-fc30-6e21-844d-57b80ea06590?origin=2", "ano": 2024, "trimestre": 4},
            # 2025
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/7032b64a-76fa-35e8-9a9b-289500684f5e?origin=2", "ano": 2025, "trimestre": 1},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/57f5564c-86cd-3bfc-9e90-02cc31cedf83?origin=2", "ano": 2025, "trimestre": 2},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/ea3b91b3-e13d-f64e-2570-033067e56514?origin=2", "ano": 2025, "trimestre": 3},
            {"url": "https://api.mziq.com/mzfilemanager/v2/d/330c258b-6212-45ce-8c13-557ea46cc23a/948c0dff-d5cd-f79d-af4c-c81b48810e1e?origin=2", "ano": 2025, "trimestre": 4},
        ],
        "general_shopping": [
            # 2023
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=EtpmxLLzbTrGp6yBJWtjpw==", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=EJHa8rCjnz0hGSk6pN2/Ug==", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=iiyh/4FPaM7Sga2iqZZ5ag==", "ano": 2025, "trimestre": 3},
            # 2024
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=gEud9fcd9j7FqcNGIxxc2Q==", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=SeCynobzSVntib/bs8MGJQ==", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=191pnX7SH4kr21AA5Hljxg==", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=QLkfqXoJ8GjrL1Jl0LQlKQ==", "ano": 2024, "trimestre": 4},
        ],
    }

    def _extrair_tri_ano(self, texto: str) -> tuple[int | None, int | None]:
        """Tenta extrair (ano, trimestre) a partir do texto."""
        match = TRI_ANO_RE.search(texto)
        if not match:
            return None, None
        trimestre = int(match.group(1))
        ano_raw = int(match.group(2))
        ano = ano_raw if ano_raw > 99 else 2000 + ano_raw
        return ano, trimestre

    def _scraping_html(self, grupo_key: str, config: dict) -> list[dict]:
        """Descobre releases via scraping HTML (Iguatemi, General Shopping)."""
        releases_url = config["releases_url"]
        keywords = config["keywords"]
        extensoes = config["extensoes"]
        releases: list[dict] = []

        try:
            logger.info(f"Scraping HTML: {releases_url}")
            resp = requests.get(
                releases_url,
                headers=HEADERS,
                timeout=settings.HTTP_TIMEOUT,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                texto = link.get_text(strip=True).lower()
                href_lower = href.lower()

                tem_keyword = any(kw in texto or kw in href_lower for kw in keywords)
                tem_extensao = any(href_lower.endswith(ext) for ext in extensoes)

                # Para sites com Download.aspx, considerar links com esse padrão
                tem_download = "download.aspx" in href_lower

                if not (tem_keyword or tem_extensao or tem_download):
                    continue

                url_absoluta = urljoin(releases_url, href)
                ano, trimestre = self._extrair_tri_ano(texto + " " + href)

                nome_arquivo = href.split("/")[-1].split("?")[0]
                if not nome_arquivo or nome_arquivo == "Download.aspx":
                    nome_arquivo = f"{grupo_key}_release"
                    if ano and trimestre:
                        nome_arquivo = f"{grupo_key}_{trimestre}T{ano}_release.pdf"

                releases.append({
                    "url": url_absoluta,
                    "nome_arquivo": nome_arquivo,
                    "ano": ano,
                    "trimestre": trimestre,
                    "tipo": "pdf",
                    "fonte": "scraping",
                    "grupo": grupo_key,
                })

            # Filtrar apenas releases que têm trimestre/ano definidos e URL de download
            releases_com_periodo = [
                r for r in releases
                if r["ano"] and r["trimestre"] and "download.aspx" in r["url"].lower()
            ]
            if releases_com_periodo:
                releases = releases_com_periodo
                logger.info(f"Scraping HTML encontrou {len(releases)} releases com periodo para {grupo_key}")
            else:
                # Scraping retornou links mas sem periodo extraível — forçar fallback
                logger.info(f"Scraping HTML encontrou {len(releases)} links mas sem periodo — forçando fallback")
                releases = []

        except requests.RequestException as e:
            logger.warning(f"Falha no scraping de {grupo_key}: {e}. Usando fallback.")

        return releases

    def descobrir_releases(self, grupo_key: str) -> list[dict]:
        """Descobre releases disponíveis para o grupo.

        Estratégia por grupo:
        - Multiplan, Allos: API MZ Group (confiável, URLs diretas)
        - Iguatemi, General Shopping: Scraping HTML + fallback com hashes conhecidos
        """
        config = self.GRUPOS_CONFIG.get(grupo_key)
        if not config:
            logger.error(f"Grupo desconhecido: {grupo_key}")
            return []

        metodo = config.get("metodo", "scraping_html")
        releases: list[dict] = []

        # Método 1: API MZ Group (Multiplan, Allos)
        if metodo == "api_mz" and grupo_key in MZ_COMPANIES:
            releases = _buscar_releases_mz(grupo_key)
            if releases:
                logger.info(f"API MZ retornou {len(releases)} releases para {grupo_key}")
                return releases
            logger.warning(f"API MZ falhou para {grupo_key}, usando fallback")

        # Método 2: Scraping HTML (Iguatemi, General Shopping)
        if metodo == "scraping_html":
            releases = self._scraping_html(grupo_key, config)

        # Fallback: URLs pré-catalogadas se scraping retornou pouco
        if len(releases) < 3:
            logger.info(f"Usando fallback RELEASES_CONHECIDOS para {grupo_key}")
            conhecidos = self.RELEASES_CONHECIDOS.get(grupo_key, [])
            urls_ja_encontradas = {r["url"] for r in releases}
            for rc in conhecidos:
                if rc["url"] not in urls_ja_encontradas:
                    releases.append({
                        "url": rc["url"],
                        "nome_arquivo": f"{grupo_key}_{rc['trimestre']}T{rc['ano']}_release.pdf",
                        "ano": rc["ano"],
                        "trimestre": rc["trimestre"],
                        "tipo": "pdf",
                        "fonte": "catalogo_manual",
                        "grupo": grupo_key,
                    })

        return releases

    def listar_todos_os_grupos(self) -> list[str]:
        return list(self.GRUPOS_CONFIG.keys())
