"""SQLAlchemy async backend composition root."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from authkit.adapters.sqlalchemy.repositories import (
    SQLAlchemyAuditSink,
    SQLAlchemyOAuthStateStore,
    SQLAlchemyRBACStore,
    SQLAlchemyRefreshTokenStore,
    SQLAlchemySessionStore,
    SQLAlchemyTokenBlacklist,
    SQLAlchemyUserStore,
)


def normalize_async_url(database_url: str) -> str:
    """Convert common sync-looking URLs to official async driver URLs."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("sqlite://") and not database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return database_url


class SQLAlchemyBackend:
    """Official SQLAlchemy 2.x async AuthKit backend.

    Construction creates an engine/pool but performs no database I/O. Schema
    ownership remains with packaged Alembic migrations.
    """

    def __init__(
        self,
        database_url: str | None = None,
        *,
        engine: AsyncEngine | None = None,
        engine_options: dict | None = None,
    ) -> None:
        if (database_url is None) == (engine is None):
            raise ValueError("Pass exactly one of database_url= or engine=")
        self.engine = engine or create_async_engine(
            normalize_async_url(database_url or ""),
            pool_pre_ping=True,
            **(engine_options or {}),
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._users = SQLAlchemyUserStore(self.session_factory)
        self._rbac = SQLAlchemyRBACStore(self.session_factory)
        self._sessions = SQLAlchemySessionStore(self.session_factory)
        self._audit = SQLAlchemyAuditSink(self.session_factory)
        self._token_blacklist = SQLAlchemyTokenBlacklist(self.session_factory)
        self._oauth_states = SQLAlchemyOAuthStateStore(self.session_factory)
        self._refresh_tokens = SQLAlchemyRefreshTokenStore(self.session_factory)

    @property
    def users(self) -> SQLAlchemyUserStore:
        return self._users

    @property
    def rbac(self) -> SQLAlchemyRBACStore:
        return self._rbac

    @property
    def sessions(self) -> SQLAlchemySessionStore:
        return self._sessions

    @property
    def audit(self) -> SQLAlchemyAuditSink:
        return self._audit

    @property
    def token_blacklist(self) -> SQLAlchemyTokenBlacklist:
        return self._token_blacklist

    @property
    def oauth_states(self) -> SQLAlchemyOAuthStateStore:
        return self._oauth_states

    @property
    def refresh_tokens(self) -> SQLAlchemyRefreshTokenStore:
        return self._refresh_tokens

    async def close(self) -> None:
        """Dispose the owned engine/pool."""
        await self.engine.dispose()
