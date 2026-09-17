"""Official SQLAlchemy 2.x async adapter.

Importing this module requires the ``sqlalchemy`` or ``postgres`` extra. The
AuthKit core never imports this adapter.
"""

try:
    from authkit.adapters.sqlalchemy.backend import SQLAlchemyBackend
    from authkit.adapters.sqlalchemy.models import Base, metadata
except ImportError as exc:  # pragma: no cover - exercised by clean minimal installs
    if exc.name and (exc.name.startswith("sqlalchemy") or exc.name == "alembic"):
        raise ImportError(
            "The SQLAlchemy adapter requires an optional extra. Install "
            "'authkit[sqlalchemy]' for SQLite or 'authkit[postgres]' for PostgreSQL."
        ) from exc
    raise

__all__ = ["Base", "SQLAlchemyBackend", "metadata"]
