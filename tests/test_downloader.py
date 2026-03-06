import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.downloader import Manifesto, ReleaseDownloader


class TestManifesto:
    def test_registrar_e_relatorio(self, tmp_path):
        manifesto = Manifesto(base_dir=tmp_path)
        release = {"url": "https://example.com/release.pdf", "grupo": "multiplan", "ano": 2024, "trimestre": 3}
        manifesto.registrar(release, "/tmp/release.pdf", "ok", "abc123", 1024, None)

        rel = manifesto.relatorio()
        assert rel["total"] == 1
        assert rel["ok"] == 1
        assert rel["erro"] == 0

    def test_ja_baixado(self, tmp_path):
        manifesto = Manifesto(base_dir=tmp_path)
        url = "https://example.com/release.pdf"
        release = {"url": url, "grupo": "multiplan", "ano": 2024, "trimestre": 3}

        assert not manifesto.ja_baixado(url)
        manifesto.registrar(release, "/tmp/release.pdf", "ok", "abc123", 1024, None)
        assert manifesto.ja_baixado(url)

    def test_persistencia_em_disco(self, tmp_path):
        manifesto = Manifesto(base_dir=tmp_path)
        release = {"url": "https://example.com/release.pdf", "grupo": "test", "ano": 2024, "trimestre": 1}
        manifesto.registrar(release, "/tmp/r.pdf", "ok", "md5", 100, None)

        # Recria a partir do disco
        manifesto2 = Manifesto(base_dir=tmp_path)
        assert manifesto2.relatorio()["total"] == 1


class TestReleaseDownloader:
    @patch("app.services.downloader.settings")
    def test_validar_arquivo_pdf(self, mock_settings, tmp_path):
        mock_settings.RELEASES_DIR = tmp_path
        mock_settings.HTTP_TIMEOUT = 10
        mock_settings.HTTP_DELAY = 0
        mock_settings.HTTP_RETRY = 1

        downloader = ReleaseDownloader()

        # Cria arquivo PDF fake
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")
        assert downloader._validar_arquivo(pdf_file)

    @patch("app.services.downloader.settings")
    def test_validar_arquivo_xlsx(self, mock_settings, tmp_path):
        mock_settings.RELEASES_DIR = tmp_path
        mock_settings.HTTP_TIMEOUT = 10
        mock_settings.HTTP_DELAY = 0
        mock_settings.HTTP_RETRY = 1

        downloader = ReleaseDownloader()

        # Cria arquivo XLSX fake (ZIP magic bytes)
        xlsx_file = tmp_path / "test.xlsx"
        xlsx_file.write_bytes(b"PK\x03\x04 fake xlsx")
        assert downloader._validar_arquivo(xlsx_file)

    @patch("app.services.downloader.settings")
    def test_validar_arquivo_invalido(self, mock_settings, tmp_path):
        mock_settings.RELEASES_DIR = tmp_path
        mock_settings.HTTP_TIMEOUT = 10
        mock_settings.HTTP_DELAY = 0
        mock_settings.HTTP_RETRY = 1

        downloader = ReleaseDownloader()

        html_file = tmp_path / "test.html"
        html_file.write_bytes(b"<html>Not a PDF</html>")
        assert not downloader._validar_arquivo(html_file)

    @patch("app.services.downloader.settings")
    def test_calcular_md5(self, mock_settings, tmp_path):
        mock_settings.RELEASES_DIR = tmp_path

        downloader = ReleaseDownloader()
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test content")

        md5 = downloader._calcular_md5(test_file)
        assert len(md5) == 32  # MD5 hex digest length
        assert md5 == "9a0364b9e99bb480dd25e1f0284c8555"  # known md5 of "test content"
