from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine_kwargs: dict[str, object] = {
    "future": True,
    "pool_pre_ping": True,
    "connect_args": settings.database_connect_args,
}

if settings.uses_pgbouncer:
    connect_args = dict(settings.database_connect_args)
    connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.resolved_database_url,
    **engine_kwargs,
)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        yield db


async def close_db_engine() -> None:
    await engine.dispose()
