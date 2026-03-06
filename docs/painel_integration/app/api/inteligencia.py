"""
Rotas do painel admin que consomem a API do SMO Intelligence.
Referencia para o repositorio smo-admin-panel.

ESTE ARQUIVO DEVE SER COPIADO PARA O REPOSITORIO smo-admin-panel.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.intelligence_client import IntelligenceClient

router = APIRouter(prefix="/inteligencia", tags=["Inteligencia Competitiva"])
templates = Jinja2Templates(directory="app/templates")
client = IntelligenceClient()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_inteligencia(request: Request):
    """Pagina principal do dashboard de inteligencia competitiva."""
    concorrentes = client.get_concorrentes_rp()
    comparativo = client.get_comparativo_trimestral()
    status = client.get_status_coleta()

    return templates.TemplateResponse(
        "inteligencia/dashboard.html",
        {
            "request": request,
            "concorrentes": concorrentes,
            "comparativo": comparativo,
            "status_coleta": status,
        },
    )


@router.get("/concorrentes", response_class=HTMLResponse)
async def lista_concorrentes(request: Request):
    """Pagina com tabela detalhada dos concorrentes de Ribeirao Preto."""
    concorrentes = client.get_concorrentes_rp()

    return templates.TemplateResponse(
        "inteligencia/concorrentes.html",
        {
            "request": request,
            "concorrentes": concorrentes,
        },
    )


@router.get("/comparativo", response_class=HTMLResponse)
async def pagina_comparativo(
    request: Request,
    ano: int | None = None,
    trimestre: int | None = None,
):
    """Pagina com graficos comparativos trimestrais."""
    comparativo = client.get_comparativo_trimestral(
        ano=ano,
        trimestre=trimestre,
    )

    return templates.TemplateResponse(
        "inteligencia/comparativo.html",
        {
            "request": request,
            "comparativo": comparativo,
            "ano_filtro": ano,
            "trimestre_filtro": trimestre,
        },
    )


@router.get("/api/concorrentes-rp")
async def api_concorrentes_rp():
    """Endpoint JSON para consumo via JavaScript (graficos, AJAX)."""
    return client.get_concorrentes_rp()


@router.get("/api/comparativo")
async def api_comparativo(
    ano: int | None = None,
    trimestre: int | None = None,
):
    """Endpoint JSON para consumo via JavaScript (graficos, AJAX)."""
    return client.get_comparativo_trimestral(ano=ano, trimestre=trimestre)


@router.get("/api/status-coleta")
async def api_status_coleta():
    """Endpoint JSON com status da ultima coleta."""
    return client.get_status_coleta()
