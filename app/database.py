import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# Engine e session factory criados de forma lazy para evitar crash
# durante import caso DATABASE_URL esteja invalida no startup.
_engine = None
_async_session_local = None


def _get_engine():
    global _engine
    if _engine is None:
        url = settings.effective_database_url
        logger.info("Criando engine SQLAlchemy (lazy init)")
        _engine = create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_local


# Alias para compatibilidade com migrations/env.py e outros modulos
def get_engine():
    return _get_engine()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
