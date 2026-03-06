"""
Cliente HTTP para a API do SMO Intelligence.
Chamado pelo painel admin para buscar dados dos concorrentes.

ESTE ARQUIVO DEVE SER COPIADO PARA O REPOSITORIO smo-admin-panel.
"""
import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

INTELLIGENCE_API_URL = os.getenv("INTELLIGENCE_API_URL", "")
# INTELLIGENCE_API_URL sera a URL do Cloud Run smo-intelligence
# Ex: https://smo-intelligence-xxxx-rj.a.run.app


class IntelligenceClient:
    def __init__(self):
        self.base_url = INTELLIGENCE_API_URL
        self.timeout = 10.0

    def _get_token(self) -> str:
        """
        Gera token de identidade para autenticar no Cloud Run (no-allow-unauthenticated).
        Na VM smo-analise-vm, usa a metadata do Compute Engine.
        """
        import urllib.request
        metadata_url = (
            f"http://metadata.google.internal/computeMetadata/v1/instance/"
            f"service-accounts/default/identity"
            f"?audience={self.base_url}"
        )
        req = urllib.request.Request(
            metadata_url,
            headers={"Metadata-Flavor": "Google"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode("utf-8")

    def _headers(self) -> dict:
        try:
            token = self._get_token()
            return {"Authorization": f"Bearer {token}"}
        except Exception as e:
            logger.warning(f"Nao foi possivel obter token de identidade: {e}")
            return {}

    def get_concorrentes_rp(self) -> list[dict]:
        """Retorna dados dos concorrentes diretos de Ribeirao Preto."""
        try:
            resp = httpx.get(
                f"{self.base_url}/api/v1/resultados/concorrentes-rp",
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar concorrentes RP: {e}")
            return []

    def get_comparativo_trimestral(
        self,
        ano: Optional[int] = None,
        trimestre: Optional[int] = None,
    ) -> list[dict]:
        """Retorna serie historica comparativa."""
        params = {k: v for k, v in {"ano": ano, "trimestre": trimestre}.items() if v}
        try:
            resp = httpx.get(
                f"{self.base_url}/api/v1/resultados/comparativo",
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar comparativo: {e}")
            return []

    def get_status_coleta(self) -> dict:
        """Verifica status do ultimo ciclo de coleta."""
        try:
            resp = httpx.get(
                f"{self.base_url}/api/v1/coleta/status",
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar status coleta: {e}")
            return {}
