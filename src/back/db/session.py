from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dotenv import load_dotenv
from .base import Base

load_dotenv()
DEFAULT_DATABASE_URL = os.getenv("DEFAULT_DATABASE_URL", "postgresql+asyncpg://aletheia:aletheia@localhost:5432/aletheia")
if DEFAULT_DATABASE_URL is None:
    raise ValueError("DEFAULT_DATABASE_URL must be set in environment variables or .env file")

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "t", "yes", "y"}


def _build_engine_kwargs() -> dict:
    kwargs: dict = {
        "echo": _env_bool("DATABASE_ECHO"),
        "pool_pre_ping": True,
    }

    pool_size = os.getenv("DATABASE_POOL_SIZE")
    if pool_size:
        kwargs["pool_size"] = int(pool_size)
        kwargs["max_overflow"] = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        kwargs["pool_timeout"] = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
        kwargs["pool_recycle"] = int(os.getenv("DATABASE_POOL_RECYCLE", "1800"))
    return kwargs


async def init_engine(create_schema: bool = True) -> AsyncEngine:
    """Initialise la connexion globale SQLAlchemy et optionnellement la base."""
    global _engine, _session_factory
    if _engine is None:
        database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        _engine = create_async_engine(database_url, **_build_engine_kwargs())
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

        if create_schema:
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def shutdown_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
