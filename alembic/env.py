from __future__ import annotations

from logging.config import fileConfig
from uuid import uuid4

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base
from app.models import *  # noqa: F403

config = context.config
config.set_main_option("sqlalchemy.url", settings.resolved_database_url)


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
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine_kwargs: dict[str, object] = {
        "prefix": "sqlalchemy.",
        "poolclass": pool.NullPool,
        "connect_args": settings.database_connect_args,
    }

    if settings.uses_pgbouncer:
        connect_args = dict(settings.database_connect_args)
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"
        engine_kwargs["connect_args"] = connect_args

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        **engine_kwargs,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
