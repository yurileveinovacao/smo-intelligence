import hashlib
import json
import logging
import time
from pathlib import Path

import requests

from app.config import settings
from app.services.scraper import HEADERS, RIScraper

logger = logging.getLogger(__name__)

# Magic bytes para validar arquivos
MAGIC_PDF = b"%PDF"
MAGIC_ZIP = b"PK\x03\x04"  # .xlsx também usa ZIP


class Manifesto:
    """Persiste registro de downloads em JSON."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or settings.RELEASES_DIR / "manifests"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.base_dir / "downloads.json"
        self._data: dict = self._carregar()

    def _carregar(self) -> dict:
        if self.filepath.exists():
            with open(self.filepath, encoding="utf-8") as f:
                return json.load(f)
        return {"downloads": []}

    def _salvar(self) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)

    def registrar(
        self,
        release: dict,
        caminho: str | None,
        status: str,
        md5: str | None,
        tamanho: int | None,
        erro: str | None,
    ) -> None:
        registro = {
            "url": release["url"],
            "grupo": release.get("grupo"),
            "ano": release.get("ano"),
            "trimestre": release.get("trimestre"),
            "caminho": caminho,
            "status": status,
            "md5": md5,
            "tamanho": tamanho,
            "erro": erro,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._data["downloads"].append(registro)
        self._salvar()

    def ja_baixado(self, url: str) -> bool:
        return any(
            d["url"] == url and d["status"] == "ok"
            for d in self._data["downloads"]
        )

    def relatorio(self) -> dict:
        downloads = self._data["downloads"]
        ok = sum(1 for d in downloads if d["status"] == "ok")
        erro = sum(1 for d in downloads if d["status"] == "erro")
        ja_existe = sum(1 for d in downloads if d["status"] == "ja_existe")
        invalido = sum(1 for d in downloads if d["status"] == "invalido")
        return {
            "total": len(downloads),
            "ok": ok,
            "erro": erro,
            "ja_existe": ja_existe,
            "invalido": invalido,
            "downloads": downloads,
        }


class ReleaseDownloader:
    """Faz download de releases com retry e validação."""

    def __init__(self):
        self.scraper = RIScraper()
        self.manifesto = Manifesto()

    def _calcular_md5(self, filepath: Path) -> str:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _validar_arquivo(self, filepath: Path) -> bool:
        """Verifica magic bytes para determinar se é PDF ou XLSX válido."""
        with open(filepath, "rb") as f:
            header = f.read(8)
        return header.startswith(MAGIC_PDF) or header.startswith(MAGIC_ZIP)

    def baixar(self, release: dict, forcar: bool = False) -> dict:
        """Baixa um único release. Retorna dict com status."""
        grupo = release.get("grupo", "desconhecido")
        nome = release.get("nome_arquivo", "release.pdf")
        url = release["url"]

        # Diretório de destino: releases/<grupo>/
        dest_dir = settings.RELEASES_DIR / grupo
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / nome

        # Verifica se já existe e é válido
        if dest_path.exists() and not forcar:
            if self._validar_arquivo(dest_path):
                logger.info(f"Já existe e é válido: {dest_path}")
                self.manifesto.registrar(release, str(dest_path), "ja_existe", None, None, None)
                return {"status": "ja_existe", "caminho": str(dest_path)}

        # Download com retry e backoff exponencial
        last_error = None
        for tentativa in range(settings.HTTP_RETRY):
            try:
                logger.info(f"Baixando ({tentativa + 1}/{settings.HTTP_RETRY}): {url}")
                resp = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=settings.HTTP_TIMEOUT,
                    stream=True,
                )
                resp.raise_for_status()

                # Verifica content-type
                content_type = resp.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    erro_path = dest_dir / f"{nome}_pagina_erro.html"
                    with open(erro_path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    logger.warning(f"Recebeu HTML ao invés de PDF: {url}")
                    self.manifesto.registrar(release, str(erro_path), "invalido", None, None, "content-type HTML")
                    return {"status": "invalido", "caminho": str(erro_path), "erro": "content-type HTML"}

                # Salva o arquivo
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)

                # Valida magic bytes
                if not self._validar_arquivo(dest_path):
                    logger.warning(f"Arquivo inválido (magic bytes): {dest_path}")
                    self.manifesto.registrar(release, str(dest_path), "invalido", None, None, "magic bytes inválidos")
                    return {"status": "invalido", "caminho": str(dest_path), "erro": "magic bytes inválidos"}

                md5 = self._calcular_md5(dest_path)
                tamanho = dest_path.stat().st_size
                logger.info(f"Download OK: {dest_path} ({tamanho} bytes, md5={md5})")
                self.manifesto.registrar(release, str(dest_path), "ok", md5, tamanho, None)
                return {"status": "ok", "caminho": str(dest_path), "tamanho": tamanho, "md5": md5}

            except requests.RequestException as e:
                last_error = str(e)
                logger.warning(f"Tentativa {tentativa + 1} falhou para {url}: {e}")
                if tentativa < settings.HTTP_RETRY - 1:
                    wait = 2 ** (tentativa + 1)
                    logger.info(f"Aguardando {wait}s antes de nova tentativa...")
                    time.sleep(wait)

        self.manifesto.registrar(release, None, "erro", None, None, last_error)
        return {"status": "erro", "erro": last_error}

    def baixar_grupo(self, grupo_key: str, forcar: bool = False) -> dict:
        """Baixa todos os releases de um grupo."""
        releases = self.scraper.descobrir_releases(grupo_key)
        logger.info(f"Encontrados {len(releases)} releases para {grupo_key}")

        resultados = {"ok": 0, "erro": 0, "ja_existe": 0, "invalido": 0, "total": len(releases)}

        for release in releases:
            resultado = self.baixar(release, forcar=forcar)
            status = resultado["status"]
            resultados[status] = resultados.get(status, 0) + 1

            # Delay entre downloads
            time.sleep(settings.HTTP_DELAY)

        return resultados
