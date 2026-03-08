"""Create initial tables: grupos, shoppings, resultados_trimestrais

Revision ID: 001_initial
Revises:
Create Date: 2026-03-08 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "competitive_intel"


def upgrade() -> None:
    # Schema ja criado no env.py (CREATE SCHEMA IF NOT EXISTS)

    # Enums via SQL raw com IF NOT EXISTS (idempotente)
    conn = op.get_bind()
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
    op.create_table(
        "grupos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("ticker", sa.String(10), nullable=True),
        sa.Column("url_ri", sa.String(300), nullable=True),
        sa.Column("capital_aberto", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )

    # Tipos enum referenciados com create_type=False (ja criados acima)
    tipo_shopping_col = sa.Enum(
        "shopping", "outlet", "strip_mall", "outro",
        name="tipo_shopping", schema=SCHEMA, create_type=False,
    )
    segmento_publico_col = sa.Enum(
        "premium", "medio_alto", "medio", "popular", "outlet_premium",
        name="segmento_publico", schema=SCHEMA, create_type=False,
    )
    nivel_dado_col = sa.Enum(
        "individual", "grupo", "estimativa",
        name="nivel_dado", schema=SCHEMA, create_type=False,
    )

    # Tabela shoppings
    op.create_table(
        "shoppings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.grupos.id"), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_abreviado", sa.String(60), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("tipo", tipo_shopping_col, nullable=True),
        sa.Column("segmento_publico", segmento_publico_col, nullable=True),
        sa.Column("abl_m2", sa.Float(), nullable=True),
        sa.Column("concorrente_direto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dados_individuais_ri", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=SCHEMA,
    )

    # Tabela resultados_trimestrais
    op.create_table(
        "resultados_trimestrais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shopping_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.shoppings.id"), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("trimestre", sa.SmallInteger(), nullable=False),
        # Metricas operacionais
        sa.Column("vendas_totais", sa.Float(), nullable=True),
        sa.Column("vendas_m2", sa.Float(), nullable=True),
        sa.Column("sss", sa.Float(), nullable=True),
        sa.Column("ssr", sa.Float(), nullable=True),
        sa.Column("taxa_ocupacao", sa.Float(), nullable=True),
        sa.Column("abl_propria_m2", sa.Float(), nullable=True),
        sa.Column("fluxo_visitantes", sa.Float(), nullable=True),
        sa.Column("inadimplencia_liquida", sa.Float(), nullable=True),
        # Metricas financeiras
        sa.Column("receita_bruta", sa.Float(), nullable=True),
        sa.Column("receita_locacao", sa.Float(), nullable=True),
        sa.Column("noi", sa.Float(), nullable=True),
        sa.Column("noi_m2", sa.Float(), nullable=True),
        sa.Column("noi_margem", sa.Float(), nullable=True),
        sa.Column("ebitda_ajustado", sa.Float(), nullable=True),
        sa.Column("ebitda_margem", sa.Float(), nullable=True),
        sa.Column("ffo", sa.Float(), nullable=True),
        # Metadados
        sa.Column("nivel_dado", nivel_dado_col, nullable=True),
        sa.Column("fonte", sa.String(200), nullable=True),
        sa.Column("url_fonte", sa.String(500), nullable=True),
        sa.Column("nome_arquivo_fonte", sa.String(300), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("revisado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("shopping_id", "ano", "trimestre", name="uq_shopping_ano_tri"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("resultados_trimestrais", schema=SCHEMA)
    op.drop_table("shoppings", schema=SCHEMA)
    op.drop_table("grupos", schema=SCHEMA)

    conn = op.get_bind()
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.nivel_dado"))
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.segmento_publico"))
    conn.execute(text(f"DROP TYPE IF EXISTS {SCHEMA}.tipo_shopping"))
