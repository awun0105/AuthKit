"""Isolated Alembic environment for AuthKit-owned tables."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from authkit.adapters.sqlalchemy.backend import normalize_async_url
from authkit.adapters.sqlalchemy.models import metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

database_url = config.attributes.get("authkit_database_url") or config.get_main_option(
    "sqlalchemy.url"
)
config.set_main_option("sqlalchemy.url", normalize_async_url(database_url))
target_metadata = metadata


def configure(connection=None, *, url: str | None = None) -> None:
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        version_table="authkit_alembic_version",
        compare_type=True,
        render_as_batch=False,
    )


def run_migrations_offline() -> None:
    configure(url=config.get_main_option("sqlalchemy.url"))
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
