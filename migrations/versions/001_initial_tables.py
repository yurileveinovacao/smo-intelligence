"""Create initial tables: grupos, shoppings, resultados_trimestrais

Revision ID: 001_initial
Revises:
Create Date: 2026-03-08 17:00:00.000000
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "competitive_intel"


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 100% raw SQL para evitar bugs do sa.Enum + create_type=False
    # no PostgreSQL dialect do SQLAlchemy 2.0
    # ---------------------------------------------------------------
    conn = op.get_bind()

    # Enums (idempotente via DO/EXCEPTION)
    conn.execute(text(
        f"DO $$ BEGIN "
        f"CREATE TYPE {SCHEMA}.tipo_shopping AS ENUM "
        f"('shopping','outlet','strip_mall','outro'); "
        f"EXCEPTION WHEN duplicate_object THEN null; END $$"
    ))
    conn.execute(text(
        f"DO $$ BEGIN "
        f"CREATE TYPE {SCHEMA}.segmento_publico AS ENUM "
        f"('premium','medio_alto','medio','popular','outlet_premium'); "
        f"EXCEPTION WHEN duplicate_object THEN null; END $$"
    ))
    conn.execute(text(
        f"DO $$ BEGIN "
        f"CREATE TYPE {SCHEMA}.nivel_dado AS ENUM "
        f"('individual','grupo','estimativa'); "
        f"EXCEPTION WHEN duplicate_object THEN null; END $$"
    ))

    # Tabela grupos
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.grupos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(120) NOT NULL,
            ticker VARCHAR(10),
            url_ri VARCHAR(300),
            capital_aberto BOOLEAN NOT NULL DEFAULT true,
            ativo BOOLEAN NOT NULL DEFAULT true,
            observacoes TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))

    # Tabela shoppings
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.shoppings (
            id SERIAL PRIMARY KEY,
            grupo_id INTEGER NOT NULL REFERENCES {SCHEMA}.grupos(id),
            nome VARCHAR(200) NOT NULL,
            nome_abreviado VARCHAR(60),
            cidade VARCHAR(100),
            uf VARCHAR(2),
            tipo {SCHEMA}.tipo_shopping,
            segmento_publico {SCHEMA}.segmento_publico,
            abl_m2 DOUBLE PRECISION,
            concorrente_direto BOOLEAN NOT NULL DEFAULT false,
            dados_individuais_ri BOOLEAN NOT NULL DEFAULT false,
            observacoes TEXT,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))

    # Tabela resultados_trimestrais
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.resultados_trimestrais (
            id SERIAL PRIMARY KEY,
            shopping_id INTEGER NOT NULL REFERENCES {SCHEMA}.shoppings(id),
            ano SMALLINT NOT NULL,
            trimestre SMALLINT NOT NULL,
            vendas_totais DOUBLE PRECISION,
            vendas_m2 DOUBLE PRECISION,
            sss DOUBLE PRECISION,
            ssr DOUBLE PRECISION,
            taxa_ocupacao DOUBLE PRECISION,
            abl_propria_m2 DOUBLE PRECISION,
            fluxo_visitantes DOUBLE PRECISION,
            inadimplencia_liquida DOUBLE PRECISION,
            receita_bruta DOUBLE PRECISION,
            receita_locacao DOUBLE PRECISION,
            noi DOUBLE PRECISION,
            noi_m2 DOUBLE PRECISION,
            noi_margem DOUBLE PRECISION,
            ebitda_ajustado DOUBLE PRECISION,
            ebitda_margem DOUBLE PRECISION,
            ffo DOUBLE PRECISION,
            nivel_dado {SCHEMA}.nivel_dado,
            fonte VARCHAR(200),
            url_fonte VARCHAR(500),
            nome_arquivo_fonte VARCHAR(300),
            notas TEXT,
            revisado BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_shopping_ano_tri UNIQUE (shopping_id, ano, trimestre)
        )
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.resultados_trimestrais"))
    conn.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.shoppings"))
    conn.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.grupos"))
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.nivel_dado"))
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.segmento_publico"))
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.tipo_shopping"))
