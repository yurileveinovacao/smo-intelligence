"""
Script de extracao de metricas dos releases trimestrais.
Le cada PDF de release e extrai metricas operacionais e financeiras.
Salva os dados em JSON em docs/extracted/{grupo}/{ano}Q{trimestre}.json
"""
import json
import re
import warnings
from datetime import date
from pathlib import Path

import pdfplumber

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DOCS = BASE / "docs"
EXTRACTED = DOCS / "extracted"

# ── helpers ──────────────────────────────────────────────────────────

def clean_number(txt: str) -> float | None:
    """Converte texto numerico BR para float. Ex: '1.234,5' -> 1234.5"""
    if not txt or txt.strip() in ("", "-", "n.d.", "N/D", "n/a"):
        return None
    txt = txt.strip().replace(" ", "")
    # Remove unidade M, mil, etc - mas nao remove pontos/virgulas
    txt = re.sub(r'[Rr$%]', '', txt)
    txt = txt.strip()
    if not txt:
        return None
    # Formato BR: 1.234,5 -> 1234.5
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def extract_all_text(pdf_path: str) -> str:
    """Extrai todo o texto de um PDF."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            full_text += txt + "\n"
    return full_text


def find_metric(text: str, patterns: list[str], min_val: float = 0, max_val: float = 1e12) -> float | None:
    """
    Tenta encontrar uma metrica usando multiplos patterns em ordem de prioridade.
    Retorna o primeiro valor valido dentro do intervalo [min_val, max_val].
    """
    for pat in patterns:
        matches = re.finditer(pat, text, re.IGNORECASE)
        for m in matches:
            val = clean_number(m.group(1))
            if val is not None and min_val <= val <= max_val:
                return val
    return None


def find_pct(text: str, patterns: list[str], min_val: float = -100, max_val: float = 200) -> float | None:
    """Busca percentual no texto."""
    return find_metric(text, patterns, min_val, max_val)


# ── Multiplan extraction ─────────────────────────────────────────────

def extract_multiplan(pdf_path: str, ano: int, tri: int) -> dict:
    """Extrai metricas de um release da Multiplan."""
    text = extract_all_text(pdf_path)
    tri_label = f"{tri}T{ano % 100:02d}"  # ex: "1T24"
    data = {
        "grupo": "multiplan",
        "ano": ano,
        "trimestre": tri,
        "arquivo_origem": str(Path(pdf_path).relative_to(DOCS)),
        "data_extracao": str(date.today()),
        "nivel_grupo": {},
        "nivel_shopping": [],
        "notas": ""
    }
    ng = {}

    # Receita Bruta - busca em DRE (R$ mil) ou texto corrido (R$ milhoes)
    ng["receita_bruta"] = find_metric(text, [
        # Padrao DRE: "Receita Bruta 563.981 516.204"
        r'Receita\s+Bruta\s+(\d{3}[.,]\d{3})',
        # "Receita Bruta de R$563,9"
        r'Receita\s+Bruta\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        # Padrao tabela: "Receita Bruta" seguido de numero
        r'Receita\s+Bruta\s+(\d[\d.,]+)',
    ], min_val=50)

    # NOI - busca pelo valor trimestral, nao a serie historica
    ng["noi"] = find_metric(text, [
        # "NOI R$'000 419.101" (suplemento)
        r"NOI\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        # "NOI de R$419,1" ou "NOI foi de R$419,1"
        r'NOI\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        # DRE: "NOI 419.101 386.123"
        r'\bNOI\b\s+(\d{3}[.,]\d{3})',
    ], min_val=10)

    # Margem NOI
    ng["noi_margem"] = find_pct(text, [
        r'[Mm]argem\s+NOI\s+[^0-9]*(\d[\d.,]+)\s*%',
        r'NOI\s*%\s+(\d[\d.,]+)',
    ], min_val=50, max_val=100)

    # EBITDA - busca trimestral em R$ mil ou R$ milhoes
    ng["ebitda_ajustado"] = find_metric(text, [
        # "EBITDA R$'000 390.824" (suplemento)
        r"EBITDA\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        # "EBITDA da Companhia foi de R$390,8"
        r'EBITDA\s+(?:da\s+Companhia\s+)?(?:foi\s+de\s+|de\s+)?R\$\s*(\d[\d.,]+)',
        # DRE: "EBITDA 390.824 357.693"
        r'\bEBITDA\b\s+(\d{3}[.,]\d{3})',
    ], min_val=50)

    # FFO
    ng["ffo"] = find_metric(text, [
        r"FFO\s+R\$['\u2019]000\s+(\d[\d.,]+)",
        r'FFO\s+(?:Ajustado\s+)?(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bFFO\b\s+(\d{3}[.,]\d{3})',
    ], min_val=10)

    # Taxa de ocupacao
    ng["taxa_ocupacao"] = find_pct(text, [
        r'[Tt]axa\s+de\s+[Oo]cupa[cC\xe7][aA\xe3]o\s+(?:de\s+|foi\s+de\s+|atingiu\s+)?(\d[\d.,]+)\s*%',
        r'[Oo]cupa[cC\xe7][aA\xe3]o[^0-9]{0,30}(\d{2}[.,]\d)\s*%',
    ], min_val=70, max_val=100)

    # Inadimplencia liquida
    ng["inadimplencia_liquida"] = find_pct(text, [
        r'[Ii]nadimpl[eE\xea]ncia\s+[Ll][iI\xed]quida\s+[^0-9]*?([+-]?\d[\d.,]+)\s*%',
        r'[Ii]nadimpl[eE\xea]ncia\s+[Ll][iI\xed]quida\s+[^0-9]*?([+-]?\d[\d.,]+)',
    ], min_val=-10, max_val=30)

    # SSS
    ng["sss"] = find_pct(text, [
        r'(?:SSS|Same\s+Store\s+Sales?)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # SSR
    ng["ssr"] = find_pct(text, [
        r'(?:SSR|Same\s+Store\s+Rent|[Aa]luguel\s+[Nn]as\s+[Mm]esmas\s+[Ll]ojas)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # Vendas Totais (em R$ milhoes/bilhoes)
    # Cuidado: Multiplan coloca "base 100%" na pagina 5
    ng["vendas_totais"] = find_metric(text, [
        # "Vendas totais de R$ 5,4 bilhoes"
        r'[Vv]endas\s+[Tt]otais\s+(?:dos\s+lojistas\s+)?(?:de\s+)?R\$\s*(\d[\d.,]+)',
        # Em tabela, procura valores > 1000 (R$ milhoes)
        r'[Vv]endas\s+[Tt]otais[^0-9]{0,30}(\d{1,2}[.,]\d{3})',
    ], min_val=500)

    # ABL propria
    ng["abl_propria_m2"] = find_metric(text, [
        r'ABL\s+[Pp]r[oO\xf3]pria[^0-9]{0,30}(\d[\d.,]+)\s*m',
        r'ABL\s+[Pp]r[oO\xf3]pria[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=100)

    # Receita de locacao
    ng["receita_locacao"] = find_metric(text, [
        r'[Rr]eceita\s+de\s+[Ll]oca[cC\xe7][aA\xe3]o\s+(\d[\d.,]+)',
        r'[Rr]eceita\s+de\s+[Aa]luguel\s+(\d[\d.,]+)',
    ], min_val=50)

    data["nivel_grupo"] = ng
    data["notas"] = "Multiplan publica dados consolidados no release. Dados individuais por shopping disponiveis no Suplemento Operacional (planilha de fundamentos)."
    return data


# ── Iguatemi extraction ──────────────────────────────────────────────

def extract_iguatemi(pdf_path: str, ano: int, tri: int) -> dict:
    text = extract_all_text(pdf_path)
    data = {
        "grupo": "iguatemi",
        "ano": ano,
        "trimestre": tri,
        "arquivo_origem": str(Path(pdf_path).relative_to(DOCS)),
        "data_extracao": str(date.today()),
        "nivel_grupo": {},
        "nivel_shopping": [],
        "notas": ""
    }
    ng = {}

    # Receita Bruta - Iguatemi usa R$ milhoes
    ng["receita_bruta"] = find_metric(text, [
        # "Receita Bruta de R$ 297,5"
        r'[Rr]eceita\s+[Bb]ruta\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        # DRE: "Receita Bruta 297.540"
        r'[Rr]eceita\s+[Bb]ruta\s+(\d{3}[.,]\d{3})',
        # Tabela: "Receita Bruta" + numero
        r'[Rr]eceita\s+[Bb]ruta\s+(\d[\d.,]+)',
    ], min_val=50)

    # NOI
    ng["noi"] = find_metric(text, [
        r'NOI\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bNOI\b\s+(\d{3}[.,]\d{3})',
        r'\bNOI\b\s+(\d[\d.,]+)',
    ], min_val=10)

    # Margem NOI
    ng["noi_margem"] = find_pct(text, [
        r'[Mm]argem\s+NOI\s+[^0-9]*(\d[\d.,]+)\s*%',
        r'[Mm]argem\s+NOI\s+[^0-9]*(\d[\d.,]+)',
    ], min_val=50, max_val=100)

    # EBITDA
    ng["ebitda_ajustado"] = find_metric(text, [
        r'EBITDA\s+[Aa]justado\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'EBITDA\s+[Aa]justado\s+(\d{3}[.,]\d{3})',
        r'EBITDA\s+[Aa]justado[^0-9]{0,30}(\d[\d.,]+)',
        r'\bEBITDA\b\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bEBITDA\b\s+(\d{3}[.,]\d{3})',
    ], min_val=30)

    # FFO
    ng["ffo"] = find_metric(text, [
        r'FFO\s+[Aa]justado\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'FFO\s+[Aa]justado\s+(\d{3}[.,]\d{3})',
        r'FFO\s+[Aa]justado[^0-9]{0,30}(\d[\d.,]+)',
        r'\bFFO\b\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bFFO\b\s+(\d{3}[.,]\d{3})',
    ], min_val=10)

    # Taxa de ocupacao
    ng["taxa_ocupacao"] = find_pct(text, [
        r'[Tt]axa\s+de\s+[Oo]cupa[cC\xe7][aA\xe3]o\s+[^0-9]*?(\d[\d.,]+)\s*%',
        r'[Oo]cupa[cC\xe7][aA\xe3]o[^0-9]{0,30}(\d{2}[.,]\d)\s*%',
    ], min_val=70, max_val=100)

    # Inadimplencia liquida
    ng["inadimplencia_liquida"] = find_pct(text, [
        r'[Ii]nadimpl[eE\xea]ncia\s+[Ll][iI\xed]quida[^0-9]*?([+-]?\d[\d.,]+)\s*%',
    ], min_val=-10, max_val=30)

    # SSS
    ng["sss"] = find_pct(text, [
        r'(?:SSS|Same\s+Store\s+Sales?)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # SSR
    ng["ssr"] = find_pct(text, [
        r'(?:SSR|Same\s+Store\s+Rent)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # Vendas totais
    ng["vendas_totais"] = find_metric(text, [
        r'[Vv]endas\s+(?:[Tt]otais|dos\s+[Ll]ojistas)\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'[Vv]endas\s+(?:[Tt]otais|dos\s+[Ll]ojistas)\s+(\d{1,2}[.,]\d{3})',
    ], min_val=500)

    ng["abl_propria_m2"] = None
    ng["receita_locacao"] = None

    data["nivel_grupo"] = ng
    data["notas"] = "Iguatemi nao publica dados individuais por shopping no release. Dados consolidados do grupo."
    return data


# ── Allos extraction ─────────────────────────────────────────────────

def extract_allos(pdf_path: str, ano: int, tri: int) -> dict:
    text = extract_all_text(pdf_path)
    data = {
        "grupo": "allos",
        "ano": ano,
        "trimestre": tri,
        "arquivo_origem": str(Path(pdf_path).relative_to(DOCS)),
        "data_extracao": str(date.today()),
        "nivel_grupo": {},
        "nivel_shopping": [],
        "notas": ""
    }
    ng = {}

    # Receita Bruta
    ng["receita_bruta"] = find_metric(text, [
        r'[Rr]eceita\s+[Bb]ruta\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'[Rr]eceita\s+[Bb]ruta\s+(\d{3}[.,]\d{3})',
        r'[Rr]eceita\s+[Bb]ruta\s+(\d[\d.,]+)',
    ], min_val=100)

    # NOI
    ng["noi"] = find_metric(text, [
        r'\bNOI\b\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bNOI\b\s+(\d{3}[.,]\d{3})',
    ], min_val=50)

    # Margem NOI
    ng["noi_margem"] = find_pct(text, [
        r'[Mm]argem\s+NOI[^0-9]*?(\d[\d.,]+)\s*%',
        r'[Mm]argem\s+NOI[^0-9]*?(\d[\d.,]+)',
    ], min_val=50, max_val=100)

    # EBITDA
    ng["ebitda_ajustado"] = find_metric(text, [
        r'EBITDA\s+[Aa]justado\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'EBITDA\s+[Aa]justado\s+(\d{3}[.,]\d{3})',
        r'EBITDA\s+[Aa]justado[^0-9]{0,30}(\d[\d.,]+)',
        r'\bEBITDA\b\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bEBITDA\b\s+(\d{3}[.,]\d{3})',
    ], min_val=50)

    # FFO
    ng["ffo"] = find_metric(text, [
        r'FFO\s+(?:[Aa]justado\s+)?(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bFFO\b\s+(\d{3}[.,]\d{3})',
        r'\bFFO\b[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=10)

    # Taxa de ocupacao
    ng["taxa_ocupacao"] = find_pct(text, [
        r'[Tt]axa\s+de\s+[Oo]cupa[cC\xe7][aA\xe3]o[^0-9]*?(\d[\d.,]+)\s*%',
    ], min_val=70, max_val=100)

    # Inadimplencia
    ng["inadimplencia_liquida"] = find_pct(text, [
        r'[Ii]nadimpl[eE\xea]ncia\s+[Ll][iI\xed]quida[^0-9]*?([+-]?\d[\d.,]+)\s*%',
    ], min_val=-10, max_val=30)

    # SSS
    ng["sss"] = find_pct(text, [
        r'(?:SSS|Same\s+Store\s+Sales?)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # SSR
    ng["ssr"] = find_pct(text, [
        r'(?:SSR|Same\s+Store\s+Rent)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # Vendas totais
    ng["vendas_totais"] = find_metric(text, [
        r'[Vv]endas\s+[Tt]otais\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'[Vv]endas\s+[Tt]otais\s+(\d{1,2}[.,]\d{3})',
    ], min_val=500)

    ng["abl_propria_m2"] = None
    ng["receita_locacao"] = None

    data["nivel_grupo"] = ng
    data["notas"] = "Allos (fusao brMalls + Ancar jan/2023). Dados consolidados do portfolio."
    return data


# ── General Shopping extraction ──────────────────────────────────────

def extract_general_shopping(pdf_path: str, ano: int, tri: int) -> dict:
    text = extract_all_text(pdf_path)
    data = {
        "grupo": "general_shopping",
        "ano": ano,
        "trimestre": tri,
        "arquivo_origem": str(Path(pdf_path).relative_to(DOCS)),
        "data_extracao": str(date.today()),
        "nivel_grupo": {},
        "nivel_shopping": [],
        "notas": ""
    }
    ng = {}

    # Receita Bruta - GSB usa "para R$ XX,X milhoes"
    ng["receita_bruta"] = find_metric(text, [
        # "para R$ 47,1 milhoes"
        r'[Rr]eceita\s+[Bb]ruta\s+[^0-9]{0,60}R\$\s*(\d[\d.,]+)\s*milh',
        # "R$ 47,1 milhoes"
        r'[Rr]eceita\s+[Bb]ruta\s+[^0-9]{0,60}R\$\s*(\d[\d.,]+)',
        # Tabela DRE: "Receita Bruta 47.102"
        r'[Rr]eceita\s+[Bb]ruta\s+(\d{2,3}[.,]\d{3})',
    ], min_val=10, max_val=500)

    # NOI
    ng["noi"] = find_metric(text, [
        r'\bNOI\b\s+(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bNOI\b\s+(\d{2,3}[.,]\d{3})',
    ], min_val=5)

    # Margem NOI
    ng["noi_margem"] = find_pct(text, [
        r'[Mm]argem\s+NOI[^0-9]*?(\d[\d.,]+)\s*%',
        r'[Mm]argem\s+NOI[^0-9]*?(\d[\d.,]+)',
    ], min_val=30, max_val=100)

    # EBITDA
    ng["ebitda_ajustado"] = find_metric(text, [
        r'EBITDA\s+(?:[Aa]justado\s+)?(?:de\s+|foi\s+de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bEBITDA\b\s+(\d{2,3}[.,]\d{3})',
        r'\bEBITDA\b[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=5)

    # FFO
    ng["ffo"] = find_metric(text, [
        r'\bFFO\b\s+(?:[Aa]justado\s+)?(?:de\s+)?R\$\s*(\d[\d.,]+)',
        r'\bFFO\b[^0-9]{0,30}(\d[\d.,]+)',
    ], min_val=0.5)

    # Taxa de ocupacao
    ng["taxa_ocupacao"] = find_pct(text, [
        r'[Tt]axa\s+de\s+[Oo]cupa[cC\xe7][aA\xe3]o[^0-9]*?(\d[\d.,]+)\s*%',
        r'[Oo]cupa[cC\xe7][aA\xe3]o[^0-9]{0,30}(\d{2}[.,]\d)\s*%',
    ], min_val=70, max_val=100)

    # Inadimplencia
    ng["inadimplencia_liquida"] = find_pct(text, [
        r'[Ii]nadimpl[eE\xea]ncia\s+[Ll][iI\xed]quida[^0-9]*?([+-]?\d[\d.,]+)\s*%',
        r'[Ii]nadimpl[eE\xea]ncia[^0-9]*?([+-]?\d[\d.,]+)\s*%',
    ], min_val=-10, max_val=30)

    # SSS
    ng["sss"] = find_pct(text, [
        r'(?:SSS|Same\s+Store\s+Sales?)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # SSR
    ng["ssr"] = find_pct(text, [
        r'(?:SSR|Same\s+Store\s+Rent)[^0-9]{0,30}([+-]?\d[\d.,]+)\s*%',
    ], min_val=-50, max_val=100)

    # Vendas totais
    ng["vendas_totais"] = find_metric(text, [
        r'[Vv]endas\s+[Tt]otais\s+(?:de\s+)?R\$\s*(\d[\d.,]+)',
    ], min_val=50)

    ng["abl_propria_m2"] = None
    ng["receita_locacao"] = None

    data["nivel_grupo"] = ng
    data["notas"] = "General Shopping & Outlets. Dados consolidados."
    return data


# ── Mapeamento de arquivos ───────────────────────────────────────────

RELEASES = {
    "multiplan": [
        {"path": "multiplan/MULTIPLAN/2024/Relatório de resultados/Relatório de Resultados 1T24.pdf", "ano": 2024, "tri": 1},
        {"path": "multiplan/MULTIPLAN/2024/Relatório de resultados/Relatório de Resultados 2T24.pdf", "ano": 2024, "tri": 2},
        {"path": "multiplan/MULTIPLAN/2024/Relatório de resultados/Relatório de Resultados 3T24.pdf", "ano": 2024, "tri": 3},
        {"path": "multiplan/MULTIPLAN/2024/Relatório de resultados/Relatório de Resultados 4T24.pdf", "ano": 2024, "tri": 4},
        {"path": "multiplan/MULTIPLAN/2025/Relatório de resultados/Relatório de Resultados 1T25.pdf", "ano": 2025, "tri": 1},
        {"path": "multiplan/MULTIPLAN/2025/Relatório de resultados/Relatório de Resultados 2T25.pdf", "ano": 2025, "tri": 2},
    ],
    "iguatemi": [
        {"path": "iguatemi/IGUATEMI/2024/Relatório de resultados/Release 1T24 vfinal2.pdf", "ano": 2024, "tri": 1},
        {"path": "iguatemi/IGUATEMI/2024/Relatório de resultados/Release 2T24 PT vf2.pdf", "ano": 2024, "tri": 2},
        {"path": "iguatemi/IGUATEMI/2024/Relatório de resultados/Release 3T24 PT v27.pdf", "ano": 2024, "tri": 3},
        {"path": "iguatemi/IGUATEMI/2024/Relatório de resultados/Release 4T24 PT vFinal.pdf", "ano": 2024, "tri": 4},
        {"path": "iguatemi/IGUATEMI/2025/Relatório de resultados/Release 1T25 v20_reap_site_RI.pdf", "ano": 2025, "tri": 1},
        {"path": "iguatemi/IGUATEMI/2025/Relatório de resultados/Release 2T25_Final.pdf", "ano": 2025, "tri": 2},
    ],
    "allos": [
        {"path": "allos/ALLOS/2024/Relatório de Resultados/Relatório de Resultados 1T24.pdf", "ano": 2024, "tri": 1},
        {"path": "allos/ALLOS/2024/Relatório de Resultados/Relatório de Resultados 2T24.pdf", "ano": 2024, "tri": 2},
        {"path": "allos/ALLOS/2024/Relatório de Resultados/Relatório de Resultados 3T24.pdf", "ano": 2024, "tri": 3},
        {"path": "allos/ALLOS/2024/Relatório de Resultados/Relatório de Resultados 4T24.pdf", "ano": 2024, "tri": 4},
        {"path": "allos/ALLOS/2025/Relatório de resultados/Relatório de Resultados 1T25.pdf", "ano": 2025, "tri": 1},
        {"path": "allos/ALLOS/2025/Relatório de resultados/Relatório de Resultados 2T25.pdf", "ano": 2025, "tri": 2},
    ],
    "general_shopping": [
        {"path": "generals/GENERALS/2024/Release/GSB Release 1T24 Final.pdf", "ano": 2024, "tri": 1},
        {"path": "generals/GENERALS/2024/Release/GSB Release 2T24 Final.pdf", "ano": 2024, "tri": 2},
        {"path": "generals/GENERALS/2024/Release/GSB Release 3T24 Final.pdf", "ano": 2024, "tri": 3},
        {"path": "generals/GENERALS/2024/Release/GSB Release 4T24 final.pdf", "ano": 2024, "tri": 4},
        {"path": "generals/GENERALS/2025/Release/GSB Release 1T25 Final.pdf", "ano": 2025, "tri": 1},
        {"path": "generals/GENERALS/2025/Release/GSB Release 2T25 Final.pdf", "ano": 2025, "tri": 2},
    ],
}

EXTRACTORS = {
    "multiplan": extract_multiplan,
    "iguatemi": extract_iguatemi,
    "allos": extract_allos,
    "general_shopping": extract_general_shopping,
}


def main():
    total_ok = 0
    total_err = 0

    for grupo, releases in RELEASES.items():
        out_dir = EXTRACTED / grupo
        out_dir.mkdir(parents=True, exist_ok=True)
        extractor = EXTRACTORS[grupo]

        for r in releases:
            pdf_path = DOCS / r["path"]
            out_file = out_dir / f"{r['ano']}Q{r['tri']}.json"

            print(f"  [{grupo}] {r['tri']}T{r['ano']:02d}...", end=" ")

            if not pdf_path.exists():
                print(f"[FAIL] Arquivo nao encontrado: {pdf_path}")
                total_err += 1
                continue

            try:
                data = extractor(str(pdf_path), r["ano"], r["tri"])
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Count non-null metrics
                ng = data.get("nivel_grupo", {})
                filled = sum(1 for v in ng.values() if v is not None)
                total_fields = len(ng)
                print(f"[OK] ({filled}/{total_fields} metricas) -> {out_file.name}")
                total_ok += 1
            except Exception as e:
                print(f"[FAIL] Erro: {e}")
                total_err += 1

    print(f"\n{'='*60}")
    print(f"Total: {total_ok} OK, {total_err} erros de {total_ok + total_err} releases")


if __name__ == "__main__":
    main()
