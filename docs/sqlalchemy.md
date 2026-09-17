# SQLAlchemy adapter

Install `authkit[sqlalchemy]` for async SQLite or `authkit[postgres]` for
asyncpg. `SQLAlchemyBackend(database_url=...)` owns an async engine and exposes
narrow port implementations; call `await backend.close()` during application
shutdown.

PostgreSQL is the production reference. SQLite is supported for lightweight
tests/examples, not as proof of PostgreSQL compatibility. CI runs a separate
real-PostgreSQL marker.

The adapter lowercases emails/usernames before persistence and relies on unique
constraints to close concurrent registration races. PostgreSQL-specific types
or logic do not leak into core flows.
