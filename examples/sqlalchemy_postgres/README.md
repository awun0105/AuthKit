# SQLAlchemy + PostgreSQL example

```bash
docker compose -f examples/sqlalchemy_postgres/docker-compose.yml up -d
export AUTHKIT_DATABASE_URL=postgresql+asyncpg://authkit:authkit@127.0.0.1:5432/authkit
export AUTHKIT_SECRET_KEY='replace-with-at-least-32-random-bytes'
authkit db upgrade
authkit create-admin --email admin@example.com
uv run uvicorn examples.sqlalchemy_postgres.main:app --reload
```

Create project-specific roles and permissions through the optional, superuser-
protected `/auth/admin` router. Disable that router when it is not needed.
