"""
Serviço de extração de métricas de PDFs e persistência no banco.

Fluxo:
  PDF → pdfplumber (texto) → regex (métricas) → ResultadoTrimestral (banco)
"""
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado import ResultadoTrimestral, NivelDado
from app.models.shopping import Shopping

logger = logging.getLogger(__name__)

# Mapeamento grupo_key → shopping_id do portfolio consolidado
# Esses IDs correspondem aos registros "Portfolio X (Consolidado)" no banco
GRUPO_SHOPPING_MAP: dict[str, int] = {
    "multiplan": 5,
    "iguatemi": 6,
    "allos": 7,
    "general_shopping": 8,
}


# ─── Helpers de extração ─────────────────────────────────────────────────────

def _clean_number(txt: str) -> float | None:
    """Converte texto numérico BR para float. Ex: '1.234,5' -> 1234.5"""
    if not txt or txt.strip() in ("", "-", "n.d.", "N/D", "n/a"):
        return None
    txt = txt.strip().replace(" ", "")
    txt = re.sub(r'[Rr$%]', '', txt).strip()
    if not txt:
        return None
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def _find_metric(text: str, patterns: list[str],
                 min_val: float = 0, max_val: float = 1e12) -> float | None:
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = _clean_number(m.group(1))
            if val is not None and min_val <= val <= max_val:
                return val
    return None


def _find_pct(text: str, patterns: list[str],
              min_val: float = -100, max_val: float = 200) -> float | None:
    return _find_metric(text, patterns, min_val, max_val)


def _extract_text(pdf_path: str) -> str:
    """Extrai todo o texto de um PDF via pdfplumber."""
    import pdfplumber
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            full_text += txt + "\n"
    return full_text


# ─── Extratores por grupo ────────────────────────────────────────────────────

def _extract_common_metrics(text: str, grupo_key: str) -> dict:
    """Extrai métricas comuns a todos os grupos."""
    # Limites de min_val variam por grupo (General Shopping é menor)
    is_small = grupo_key == "general_shopping"
    min_receita = 10 if is_small else 50
    min_noi = 5 if is_small else 10
    min_ebitda = 5 if is_small else 30
    min_ffo = 0.5 if is_small else 10
    min_vendas = 50 if is_small else 500
    max_receita = 500 if is_small else 1e12

    metrics = {}

    # Receita Bruta
    metrics["receita_bruta"] = _find_metric(text, [
        r'[Rr]eceita\s+[Bb]ruta\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'[Rr]eceita\s+[Bb]ruta\s+(\d{3}[.,]\d{3})',
        r'[Rr]eceita\s+[Bb]ruta\s+(\d[\d.,]+)',
    ], min_val=min_receita, max_val=max_receita)

    # NOI
    metrics["noi"] = _find_metric(text, [
        r"NOI\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        r'\bNOI\b\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bNOI\b\s+(\d{2,3}[.,]\d{3})',
        r'\bNOI\b\s+(\d[\d.,]+)',
    ], min_val=min_noi)

    # Margem NOI
    min_margem = 30 if is_small else 50
    metrics["noi_margem"] = _find_pct(text, [
        r'[Mm]argem\s+NOI[^0-9]*?(\d[\d.,]+)\s*%',
        r'NOI\s*%\s+(\d[\d.,]+)',
    ], min_val=min_margem, max_val=100)

    # EBITDA
    metrics["ebitda_ajustado"] = _find_metric(text, [
        r"EBITDA\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        r'EBITDA\s+(?:[Aa]justado\s+)?(?:da\s+Companhia\s+)?(?:foi\s+de\s+|de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bEBITDA\b\s+(\d{2,3}[.,]\d{3})',
        r'\bEBITDA\b[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=min_ebitda)

    # FFO
    metrics["ffo"] = _find_metric(text, [
        r"FFO\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        r'FFO\s+(?:[Aa]justado\s+)?(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bFFO\b\s+(\d{2,3}[.,]\d{3})',
        r'\bFFO\b[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=min_ffo)

    # Taxa de ocupação
    metrics["taxa_ocupacao"] = _find_pct(text, [
        r'[Tt]axa\s+de\s+[Oo]cupa[cç][aã]o\s+(?:de\s+|foi\s+de\s+|atingiu\s+)?(\d[\d.,]+)\s*%',
        r'[Oo]cupa[cç][aã]o[^0-9]{0,30}(\d{2}[.,]\d)\s*%',
    ], min_val=70, max_val=100)

    # Inadimplência líquida
    metrics["inadimplencia_liquida"] = _find_pct(text, [
        r'[Ii]nadimpl[eê]ncia\s+[Ll][ií]quida[^0-9]*?([+-]?\d[\d.,]+)\s*%',
        r'[Ii]nadimpl[eê]ncia[^0-9]*?([+-]?\d[\d.,]+)\s*%',
    ], min_val=-10, max_val=30)

    # SSS
    metrics["sss"] = _find_pct(text, [
        r'(?:SSS|Same\s+Store\s+Sales?)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # SSR
    metrics["ssr"] = _find_pct(text, [
        r'(?:SSR|Same\s+Store\s+Rent|[Aa]luguel\s+[Nn]as\s+[Mm]esmas\s+[Ll]ojas)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # Vendas totais
    metrics["vendas_totais"] = _find_metric(text, [
        r'[Vv]endas\s+(?:[Tt]otais|dos\s+[Ll]ojistas)\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'[Vv]endas\s+(?:[Tt]otais|dos\s+[Ll]ojistas)\s+(\d{1,2}[.,]\d{3})',
    ], min_val=min_vendas)

    # ABL própria
    metrics["abl_propria_m2"] = _find_metric(text, [
        r'ABL\s+[Pp]r[oó]pria[^0-9]{0,30}(\d[\d.,]+)\s*m',
        r'ABL\s+[Pp]r[oó]pria[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=100)

    # Receita de locação
    metrics["receita_locacao"] = _find_metric(text, [
        r'[Rr]eceita\s+de\s+[Ll]oca[cç][aã]o\s+(\d[\d.,]+)',
        r'[Rr]eceita\s+de\s+[Aa]luguel\s+(\d[\d.,]+)',
    ], min_val=min_receita)

    return metrics


def extrair_metricas_pdf(pdf_path: str, grupo_key: str, ano: int, trimestre: int) -> dict:
    """Extrai métricas de um PDF de release trimestral.

    Retorna dict com as métricas extraídas (campos do ResultadoTrimestral).
    """
    logger.info("Extraindo metricas de %s (%s %dT%d)", pdf_path, grupo_key, trimestre, ano)

    try:
        text = _extract_text(pdf_path)
    except Exception as e:
        logger.error("Falha ao ler PDF %s: %s", pdf_path, e)
        return {}

    if not text.strip():
        logger.warning("PDF vazio: %s", pdf_path)
        return {}

    metrics = _extract_common_metrics(text, grupo_key)

    filled = sum(1 for v in metrics.values() if v is not None)
    logger.info("Extraidas %d/%d metricas de %s", filled, len(metrics), pdf_path)

    return metrics


# ─── Persistência no banco ───────────────────────────────────────────────────

async def salvar_resultado(
    db: AsyncSession,
    grupo_key: str,
    ano: int,
    trimestre: int,
    metrics: dict,
    fonte: str = "release_pdf",
    url_fonte: str | None = None,
    nome_arquivo: str | None = None,
) -> ResultadoTrimestral | None:
    """Insere ou atualiza um resultado trimestral no banco.

    Usa UPSERT: se já existe registro para (shopping_id, ano, trimestre),
    atualiza as métricas. Senão, cria novo.
    """
    shopping_id = GRUPO_SHOPPING_MAP.get(grupo_key)
    if not shopping_id:
        logger.error("Grupo %s nao tem shopping_id mapeado", grupo_key)
        return None

    if not metrics or all(v is None for v in metrics.values()):
        logger.warning("Nenhuma metrica extraida para %s %dT%d — nao salvando", grupo_key, trimestre, ano)
        return None

    # Busca registro existente
    stmt = select(ResultadoTrimestral).where(
        ResultadoTrimestral.shopping_id == shopping_id,
        ResultadoTrimestral.ano == ano,
        ResultadoTrimestral.trimestre == trimestre,
    )
    result = await db.execute(stmt)
    registro = result.scalar_one_or_none()

    if registro:
        logger.info("Atualizando resultado existente: %s %dT%d (id=%d)", grupo_key, trimestre, ano, registro.id)
        for campo, valor in metrics.items():
            if valor is not None and hasattr(registro, campo):
                setattr(registro, campo, valor)
        registro.fonte = fonte
        registro.url_fonte = url_fonte
        registro.nome_arquivo_fonte = nome_arquivo
    else:
        logger.info("Criando novo resultado: %s %dT%d (shopping_id=%d)", grupo_key, trimestre, ano, shopping_id)
        registro = ResultadoTrimestral(
            shopping_id=shopping_id,
            ano=ano,
            trimestre=trimestre,
            nivel_dado=NivelDado.grupo,
            fonte=fonte,
            url_fonte=url_fonte,
            nome_arquivo_fonte=nome_arquivo,
            **{k: v for k, v in metrics.items() if hasattr(ResultadoTrimestral, k)},
        )
        db.add(registro)

    await db.flush()
    logger.info("Resultado salvo: %s %dT%d — %d metricas",
                grupo_key, trimestre, ano,
                sum(1 for v in metrics.values() if v is not None))
    return registro


async def carregar_jsons_existentes(db: AsyncSession, extracted_dir: str) -> dict:
    """Carrega os JSONs já extraídos em docs/extracted/ para o banco.

    Útil para popular o banco com dados históricos sem precisar
    re-baixar e re-extrair os PDFs.
    """
    import json
    extracted_path = Path(extracted_dir)
    resultados = {"ok": 0, "erro": 0, "total": 0}

    for grupo_dir in sorted(extracted_path.iterdir()):
        if not grupo_dir.is_dir():
            continue
        grupo_key = grupo_dir.name

        for json_file in sorted(grupo_dir.glob("*.json")):
            resultados["total"] += 1
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                ano = data["ano"]
                trimestre = data["trimestre"]
                metrics = data.get("nivel_grupo", {})
                notas = data.get("notas", "")

                registro = await salvar_resultado(
                    db=db,
                    grupo_key=grupo_key,
                    ano=ano,
                    trimestre=trimestre,
                    metrics=metrics,
                    fonte="json_extraido",
                    nome_arquivo=json_file.name,
                )

                if registro:
                    if notas:
                        registro.notas = notas
                    resultados["ok"] += 1
                    logger.info("JSON carregado: %s", json_file.name)
                else:
                    resultados["erro"] += 1

            except Exception as e:
                logger.error("Falha ao carregar %s: %s", json_file, e)
                resultados["erro"] += 1

    await db.commit()
    return resultados
