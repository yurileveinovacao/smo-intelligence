from unittest.mock import MagicMock, patch

from app.services.scraper import RIScraper


class TestRIScraper:
    def setup_method(self):
        self.scraper = RIScraper()

    def test_listar_todos_os_grupos(self):
        grupos = self.scraper.listar_todos_os_grupos()
        assert "multiplan" in grupos
        assert "iguatemi" in grupos
        assert "allos" in grupos
        assert "general_shopping" in grupos
        assert len(grupos) == 4

    def test_grupo_desconhecido_retorna_vazio(self):
        releases = self.scraper.descobrir_releases("grupo_inexistente")
        assert releases == []

    def test_extrair_tri_ano_valido(self):
        ano, tri = self.scraper._extrair_tri_ano("Resultado 3T2024")
        assert ano == 2024
        assert tri == 3

    def test_extrair_tri_ano_curto(self):
        ano, tri = self.scraper._extrair_tri_ano("Release 1T23")
        assert ano == 2023
        assert tri == 1

    def test_extrair_tri_ano_sem_match(self):
        ano, tri = self.scraper._extrair_tri_ano("Relatório anual 2024")
        assert ano is None
        assert tri is None

    @patch("app.services.scraper.requests.get")
    def test_fallback_quando_scraping_falha(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        releases = self.scraper.descobrir_releases("multiplan")
        # Deve usar RELEASES_CONHECIDOS como fallback
        assert len(releases) > 0
        assert all(r["fonte"] == "catalogo_manual" for r in releases)

    @patch("app.services.scraper.requests.get")
    def test_scraping_com_html_valido(self, mock_get):
        html = """
        <html><body>
            <a href="/download/resultado_3T2024.pdf">Resultado 3T2024</a>
            <a href="/contato">Contato</a>
            <a href="/download/release_2T2024.pdf">Release 2T2024</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        releases = self.scraper.descobrir_releases("multiplan")
        # Deve encontrar os 2 links com keywords + fallback dos conhecidos
        urls_scraping = [r for r in releases if r["fonte"] == "scraping"]
        assert len(urls_scraping) == 2

    def test_releases_conhecidos_tem_todos_os_grupos(self):
        for grupo_key in self.scraper.GRUPOS_CONFIG:
            assert grupo_key in self.scraper.RELEASES_CONHECIDOS
            assert len(self.scraper.RELEASES_CONHECIDOS[grupo_key]) == 11  # 2T23 a 4T25
