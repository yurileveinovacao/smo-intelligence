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


class RIScraper:
    GRUPOS_CONFIG: dict[str, dict] = {
        "multiplan": {
            "nome": "Multiplan",
            "ticker": "MULT3",
            "ri_url": "https://ri.multiplan.com.br",
            "releases_url": "https://ri.multiplan.com.br/resultados-e-comunicados/resultados-trimestrais",
            "keywords": ["resultado", "release", "trimestre", "quarterly", "suplemento"],
            "extensoes": [".pdf", ".xlsx"],
        },
        "iguatemi": {
            "nome": "Iguatemi S.A.",
            "ticker": "IGTI11",
            "ri_url": "https://ri.iguatemi.com.br",
            "releases_url": "https://ri.iguatemi.com.br/central-de-resultados",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
        "allos": {
            "nome": "Allos",
            "ticker": "ALOS3",
            "ri_url": "https://ri.allos.com.br",
            "releases_url": "https://ri.allos.com.br/resultados",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
        "general_shopping": {
            "nome": "General Shopping",
            "ticker": "GSHP3",
            "ri_url": "https://ri.generalshopping.com.br",
            "releases_url": "https://ri.generalshopping.com.br/resultados-trimestrais",
            "keywords": ["resultado", "release", "trimestre", "quarterly"],
            "extensoes": [".pdf"],
        },
    }

    # URLs manuais pré-catalogadas como fallback (2T23 a 4T25)
    RELEASES_CONHECIDOS: dict[str, list[dict]] = {
        "multiplan": [
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=2T23_Release", "ano": 2023, "trimestre": 2},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=3T23_Release", "ano": 2023, "trimestre": 3},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=4T23_Release", "ano": 2023, "trimestre": 4},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=1T24_Release", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=2T24_Release", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=3T24_Release", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=4T24_Release", "ano": 2024, "trimestre": 4},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=1T25_Release", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=2T25_Release", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=3T25_Release", "ano": 2025, "trimestre": 3},
            {"url": "https://ri.multiplan.com.br/Download.aspx?Arquivo=4T25_Release", "ano": 2025, "trimestre": 4},
        ],
        "iguatemi": [
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=2T23", "ano": 2023, "trimestre": 2},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=3T23", "ano": 2023, "trimestre": 3},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=4T23", "ano": 2023, "trimestre": 4},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=1T24", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=2T24", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=3T24", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=4T24", "ano": 2024, "trimestre": 4},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=1T25", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=2T25", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=3T25", "ano": 2025, "trimestre": 3},
            {"url": "https://ri.iguatemi.com.br/Download.aspx?Arquivo=4T25", "ano": 2025, "trimestre": 4},
        ],
        "allos": [
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=2T23", "ano": 2023, "trimestre": 2},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=3T23", "ano": 2023, "trimestre": 3},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=4T23", "ano": 2023, "trimestre": 4},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=1T24", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=2T24", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=3T24", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=4T24", "ano": 2024, "trimestre": 4},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=1T25", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=2T25", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=3T25", "ano": 2025, "trimestre": 3},
            {"url": "https://ri.allos.com.br/Download.aspx?Arquivo=4T25", "ano": 2025, "trimestre": 4},
        ],
        "general_shopping": [
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=2T23", "ano": 2023, "trimestre": 2},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=3T23", "ano": 2023, "trimestre": 3},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=4T23", "ano": 2023, "trimestre": 4},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=1T24", "ano": 2024, "trimestre": 1},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=2T24", "ano": 2024, "trimestre": 2},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=3T24", "ano": 2024, "trimestre": 3},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=4T24", "ano": 2024, "trimestre": 4},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=1T25", "ano": 2025, "trimestre": 1},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=2T25", "ano": 2025, "trimestre": 2},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=3T25", "ano": 2025, "trimestre": 3},
            {"url": "https://ri.generalshopping.com.br/Download.aspx?Arquivo=4T25", "ano": 2025, "trimestre": 4},
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

    def descobrir_releases(self, grupo_key: str) -> list[dict]:
        """Descobre releases disponíveis no site de RI do grupo."""
        config = self.GRUPOS_CONFIG.get(grupo_key)
        if not config:
            logger.error(f"Grupo desconhecido: {grupo_key}")
            return []

        releases_url = config["releases_url"]
        keywords = config["keywords"]
        extensoes = config["extensoes"]

        releases: list[dict] = []

        try:
            logger.info(f"Acessando {releases_url}")
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

                # Verifica se link contém keywords ou extensões relevantes
                tem_keyword = any(kw in texto or kw in href_lower for kw in keywords)
                tem_extensao = any(href_lower.endswith(ext) for ext in extensoes)

                if not (tem_keyword or tem_extensao):
                    continue

                url_absoluta = urljoin(releases_url, href)
                ano, trimestre = self._extrair_tri_ano(texto + " " + href)

                nome_arquivo = href.split("/")[-1].split("?")[0]
                if not nome_arquivo:
                    nome_arquivo = f"{grupo_key}_release"

                releases.append({
                    "url": url_absoluta,
                    "nome_arquivo": nome_arquivo,
                    "ano": ano,
                    "trimestre": trimestre,
                    "tipo": "pdf",
                    "fonte": "scraping",
                    "grupo": grupo_key,
                })

            logger.info(f"Scraping encontrou {len(releases)} releases para {grupo_key}")

        except requests.RequestException as e:
            logger.warning(f"Falha no scraping de {grupo_key}: {e}. Usando fallback.")

        # Fallback: usa releases conhecidos se scraping retornou pouco
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
