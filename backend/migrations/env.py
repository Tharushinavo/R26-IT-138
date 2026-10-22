"""Async PostgreSQL Alembic environment."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.infrastructure.database import async_database_url, asyncpg_connect_args
from app.infrastructure.persistence_models import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option(
    "sqlalchemy.url",
    async_database_url(get_settings().database_url).replace("%", "%%"),
)
target_metadata = Base.metadata


def include_managed_object(object_, name: str | None, type_: str, reflected: bool, compare_to) -> bool:
    """Exclude the documented BE1 connectivity marker from schema ownership."""
    return not (type_ == "table" and reflected and name == "be1_persistence_check")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_managed_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_managed_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Same connect-args the application engine builds (`app.infrastructure.database`): a managed
    # provider's `sslmode` is stripped out of the URL by `async_database_url`, so without this the
    # migration connection would fall back to asyncpg's opportunistic default rather than the TLS
    # posture the pasted connection string actually asked for.
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=asyncpg_connect_args(get_settings().database_url),
    )
    async with connectable.connect() as connection:
        await connection.run_sync(run_sync_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
