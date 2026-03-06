"""Popula as tabelas grupos, shoppings e resultados_trimestrais com dados iniciais.

Le automaticamente os JSONs extraidos de docs/extracted/ para popular
os resultados trimestrais historicos dos concorrentes.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine
from app.models.grupo import Grupo
from app.models.resultado import NivelDado, ResultadoTrimestral
from app.models.shopping import Shopping, SegmentoPublico, TipoShopping


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = BASE_DIR / "docs" / "extracted"

# Mapeamento de nome de grupo (JSON) -> nome do shopping portfolio consolidado
GRUPO_TO_PORTFOLIO: dict[str, str] = {
    "multiplan": "Portfolio Multiplan (Consolidado)",
    "iguatemi": "Portfolio Iguatemi (Consolidado)",
    "allos": "Portfolio Allos (Consolidado)",
    "general_shopping": "Portfolio General Shopping (Consolidado)",
}


# ---------------------------------------------------------------------------
# Dados de seed: Grupos
# ---------------------------------------------------------------------------
GRUPOS_SEED = [
    {
        "nome": "Multiplan",
        "ticker": "MULT3",
        "url_ri": "https://ri.multiplan.com.br",
        "capital_aberto": True,
    },
    {
        "nome": "Iguatemi S.A.",
        "ticker": "IGTI11",
        "url_ri": "https://ri.iguatemi.com.br",
        "capital_aberto": True,
    },
    {
        "nome": "Allos",
        "ticker": "ALOS3",
        "url_ri": "https://ri.allos.com.br",
        "capital_aberto": True,
        "observacoes": "Fusao brMalls+Ancar jan/2023",
    },
    {
        "nome": "General Shopping & Outlets",
        "ticker": "GSHP3",
        "url_ri": "https://ri.generalshopping.com.br",
        "capital_aberto": True,
    },
    {
        "nome": "Independente",
        "ticker": None,
        "url_ri": None,
        "capital_aberto": False,
        "observacoes": "Condominio ordinario s/ RI",
    },
]


# ---------------------------------------------------------------------------
# Dados de seed: Shoppings
# ---------------------------------------------------------------------------
def _shoppings_seed(grupo_ids: dict[str, int]) -> list[dict]:
    """Retorna lista de shoppings com grupo_id resolvido."""
    return [
        # ------------------------------------------------------------------
        # Concorrentes diretos (Ribeirao Preto)
        # ------------------------------------------------------------------
        {
            "grupo_id": grupo_ids["Multiplan"],
            "nome": "Ribeirao Shopping",
            "nome_abreviado": "Rib Shop",
            "cidade": "Ribeirao Preto",
            "uf": "SP",
            "tipo": TipoShopping.shopping,
            "segmento_publico": SegmentoPublico.medio_alto,
            "abl_m2": 68566.0,
            "concorrente_direto": True,
            "dados_individuais_ri": True,
        },
        {
            "grupo_id": grupo_ids["Multiplan"],
            "nome": "Shopping Santa Ursula",
            "nome_abreviado": "Sta Ursula",
            "cidade": "Ribeirao Preto",
            "uf": "SP",
            "tipo": TipoShopping.shopping,
            "segmento_publico": SegmentoPublico.medio,
            "abl_m2": 23358.0,
            "concorrente_direto": True,
            "dados_individuais_ri": True,
        },
        {
            "grupo_id": grupo_ids["Iguatemi S.A."],
            "nome": "Iguatemi Ribeirao Preto",
            "nome_abreviado": "Iguat RP",
            "cidade": "Ribeirao Preto",
            "uf": "SP",
            "tipo": TipoShopping.shopping,
            "segmento_publico": SegmentoPublico.premium,
            "abl_m2": 50000.0,
            "concorrente_direto": True,
            "dados_individuais_ri": False,
            "observacoes": "ABL estimada",
        },
        {
            "grupo_id": grupo_ids["Independente"],
            "nome": "Novo Shopping Ribeirao Preto",
            "nome_abreviado": "Novo Shop RP",
            "cidade": "Ribeirao Preto",
            "uf": "SP",
            "tipo": TipoShopping.shopping,
            "segmento_publico": SegmentoPublico.popular,
            "abl_m2": 35000.0,
            "concorrente_direto": True,
            "dados_individuais_ri": False,
            "observacoes": "ABL estimada",
        },
        # ------------------------------------------------------------------
        # Portfolios consolidados (nivel grupo)
        # ------------------------------------------------------------------
        {
            "grupo_id": grupo_ids["Multiplan"],
            "nome": "Portfolio Multiplan (Consolidado)",
            "concorrente_direto": False,
            "dados_individuais_ri": True,
        },
        {
            "grupo_id": grupo_ids["Iguatemi S.A."],
            "nome": "Portfolio Iguatemi (Consolidado)",
            "concorrente_direto": False,
            "dados_individuais_ri": True,
        },
        {
            "grupo_id": grupo_ids["Allos"],
            "nome": "Portfolio Allos (Consolidado)",
            "concorrente_direto": False,
            "dados_individuais_ri": True,
        },
        {
            "grupo_id": grupo_ids["General Shopping & Outlets"],
            "nome": "Portfolio General Shopping (Consolidado)",
            "concorrente_direto": False,
            "dados_individuais_ri": True,
        },
    ]


# ---------------------------------------------------------------------------
# Seed de resultados trimestrais (leitura dos JSONs extraidos)
# ---------------------------------------------------------------------------
async def _seed_resultados(
    session: AsyncSession,
    shopping_name_to_id: dict[str, int],
) -> dict[str, int]:
    """Le JSONs de docs/extracted/ e insere resultados trimestrais.

    Retorna dict com contagem por grupo: {"multiplan": 6, ...}
    """
    counters: dict[str, int] = {}

    if not EXTRACTED_DIR.exists():
        print(f"  [WARN] Pasta {EXTRACTED_DIR} nao encontrada. Pulando seed de resultados.")
        return counters

    json_files = sorted(EXTRACTED_DIR.glob("*/*.json"))
    if not json_files:
        print("  [WARN] Nenhum JSON encontrado em docs/extracted/. Pulando seed de resultados.")
        return counters

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)

        grupo = data["grupo"]
        ano = data["ano"]
        tri = data["trimestre"]

        # Resolve shopping_id do portfolio consolidado
        portfolio_name = GRUPO_TO_PORTFOLIO.get(grupo)
        if not portfolio_name:
            print(f"  [WARN] Grupo '{grupo}' sem mapeamento de portfolio. Pulando {jf.name}")
            continue

        shopping_id = shopping_name_to_id.get(portfolio_name)
        if not shopping_id:
            print(f"  [WARN] Shopping '{portfolio_name}' nao encontrado no banco. Pulando {jf.name}")
            continue

        ng = data.get("nivel_grupo", {})

        # Monta valores para INSERT
        values = {
            "shopping_id": shopping_id,
            "ano": ano,
            "trimestre": tri,
            # Metricas operacionais
            "vendas_totais": ng.get("vendas_totais"),
            "sss": ng.get("sss"),
            "ssr": ng.get("ssr"),
            "taxa_ocupacao": ng.get("taxa_ocupacao"),
            "abl_propria_m2": ng.get("abl_propria_m2"),
            "inadimplencia_liquida": ng.get("inadimplencia_liquida"),
            # Metricas financeiras
            "receita_bruta": ng.get("receita_bruta"),
            "receita_locacao": ng.get("receita_locacao"),
            "noi": ng.get("noi"),
            "noi_margem": ng.get("noi_margem"),
            "ebitda_ajustado": ng.get("ebitda_ajustado"),
            "ffo": ng.get("ffo"),
            # Metadados
            "nivel_dado": NivelDado.grupo,
            "fonte": "release_pdf",
            "nome_arquivo_fonte": data.get("arquivo_origem"),
            "notas": data.get("notas"),
            "revisado": False,  # extracao automatica, precisa revisao manual
        }

        stmt = (
            insert(ResultadoTrimestral)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_shopping_ano_tri"
            )
        )
        await session.execute(stmt)

        counters[grupo] = counters.get(grupo, 0) + 1

        # Conta metricas nao-nulas para log
        metricas = [
            "receita_bruta", "noi", "noi_margem", "ebitda_ajustado", "ffo",
            "taxa_ocupacao", "inadimplencia_liquida", "sss", "ssr",
            "vendas_totais", "abl_propria_m2", "receita_locacao",
        ]
        n_metricas = sum(1 for m in metricas if ng.get(m) is not None)
        print(f"  [{grupo:<20s}] {tri}T{ano}  ({n_metricas:>2}/12 metricas)")

    return counters


# ---------------------------------------------------------------------------
# Funcao principal de seed
# ---------------------------------------------------------------------------
async def seed():
    async with AsyncSessionLocal() as session:
        session: AsyncSession

        # Cria schema se nao existir
        await session.execute(text("CREATE SCHEMA IF NOT EXISTS competitive_intel"))
        await session.commit()

        # ==================================================================
        # 1) Seed de grupos e shoppings
        # ==================================================================
        result = await session.execute(
            text("SELECT COUNT(*) FROM competitive_intel.grupos")
        )
        count = result.scalar()

        if count and count > 0:
            print(f"Banco ja possui {count} grupos. Pulando seed de grupos/shoppings.")
        else:
            print("=== Seed de grupos ===")
            grupo_ids: dict[str, int] = {}
            for g_data in GRUPOS_SEED:
                grupo = Grupo(**g_data)
                session.add(grupo)
                await session.flush()
                grupo_ids[g_data["nome"]] = grupo.id
                print(f"  Grupo criado: {grupo.nome} (id={grupo.id})")

            print("\n=== Seed de shoppings ===")
            shoppings_data = _shoppings_seed(grupo_ids)
            for s_data in shoppings_data:
                shopping = Shopping(**s_data)
                session.add(shopping)
                await session.flush()
                print(f"  Shopping criado: {shopping.nome} (id={shopping.id})")

            await session.commit()
            print(
                f"\nSeed concluido: {len(GRUPOS_SEED)} grupos, "
                f"{len(shoppings_data)} shoppings\n"
            )

        # ==================================================================
        # 2) Seed de resultados trimestrais (dados historicos extraidos)
        # ==================================================================
        print("=== Seed de resultados trimestrais ===")

        # Monta mapeamento nome_shopping -> id
        rows = await session.execute(select(Shopping.id, Shopping.nome))
        shopping_name_to_id: dict[str, int] = {
            row.nome: row.id for row in rows
        }

        counters = await _seed_resultados(session, shopping_name_to_id)
        await session.commit()

        # Resumo final
        total = sum(counters.values())
        print(f"\n{'='*60}")
        print(f"Resultados trimestrais inseridos: {total} registros")
        for grupo, n in sorted(counters.items()):
            print(f"  {grupo:<20s}: {n} trimestres")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(seed())
