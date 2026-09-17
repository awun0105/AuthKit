"""Programmatic access to AuthKit's isolated Alembic history."""

from __future__ import annotations

from importlib.resources import files

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str) -> Config:
    migrations = files("authkit.adapters.sqlalchemy").joinpath("migrations")
    config = Config()
    config.set_main_option("script_location", str(migrations))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["authkit_database_url"] = database_url
    return config


def upgrade(database_url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(database_url), revision)


def current(database_url: str) -> None:
    command.current(alembic_config(database_url), verbose=True)


def history(database_url: str) -> None:
    command.history(alembic_config(database_url), verbose=True)
