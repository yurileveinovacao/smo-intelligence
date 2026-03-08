import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base

# Importa todos os models para que Base.metadata conheça as tabelas
import app.models  # noqa: F401

config = context.config
# Escapa % para %% pois configparser interpreta % como interpolacao
config.set_main_option(
    "sqlalchemy.url",
    settings.effective_database_url.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="competitive_intel",
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="competitive_intel",
        include_schemas=True,
    )

    with context.begin_transaction():
        context.execute(text("CREATE SCHEMA IF NOT EXISTS competitive_intel"))
        context.run_migrations()


async def run_async_migrations() -> None:
    # Usa create_async_engine direto com a URL das settings
    # (evita configparser que interpreta % como interpolacao)
    connectable = create_async_engine(
        settings.effective_database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
