# AuthKit

AuthKit is a reusable full-stack authentication and authorization foundation
for FastAPI applications, with optional TypeScript/React/Next.js packages.
The Python library stays storage-agnostic and ships official in-memory and
SQLAlchemy 2.x async backends. Frontend packages are optional and are never
installed by `uv add authkit`.

It grew from the MIT-licensed AuthWarden project. AuthWarden's password, JWT,
OAuth/PKCE, MFA, notification, lockout, anti-enumeration, and single-use token
behavior remains the security foundation; see [third-party notices](THIRD_PARTY_NOTICES.md).

AuthKit provides registration, login/logout, access and rotating refresh JWTs,
password reset/change, verification, optional OAuth and MFA, database-backed
roles/permissions, sessions, audit events, isolated migrations, a small public
gateway, and lifecycle events. It is an application library—not an OAuth
authorization server, IdP, general-purpose UI framework, or Keycloak replacement.

## Install

```bash
uv add authkit                         # memory/custom storage
uv add "authkit[sqlalchemy]"          # SQLAlchemy + SQLite support
uv add "authkit[postgres]"            # SQLAlchemy + asyncpg
uv add "authkit[redis]"               # Redis session/revocation options
```

## Smallest working application

```python
from fastapi import Depends, FastAPI
from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend

backend = MemoryBackend()  # development/tests only
auth = AuthKit(
    config=AuthKitConfig(
        secret_key="replace-with-at-least-32-random-bytes",
        require_email_verification=False,
    ),
    backend=backend,
)

app = FastAPI()
app.include_router(auth.router, prefix="/auth")

@app.get("/me")
async def me(user=Depends(auth.current_user)):
    return user.to_read()

@app.post(
    "/documents",
    dependencies=[Depends(auth.require_permission("documents.create"))],
)
async def create_document():
    return {"created": True}
```

Run `uvicorn main:app --reload`, then use `/docs` for register, login, refresh,
logout, verification, password, OAuth, and MFA endpoints. OAuth and MFA require
no credentials/configuration when disabled.

## PostgreSQL and migrations

```python
from authkit.adapters.sqlalchemy import SQLAlchemyBackend

backend = SQLAlchemyBackend(database_url=settings.database_url)
auth = AuthKit(
    config=AuthKitConfig(secret_key=settings.auth_secret),
    backend=backend,
)
```

```bash
export AUTHKIT_DATABASE_URL='postgresql+asyncpg://user:pass@localhost/app'
authkit db upgrade
authkit db current
```

AuthKit owns only `authkit_*` tables and uses
`authkit_alembic_version`, so the consuming application's Alembic history and
tables remain separate. See [migration integration](docs/migrations.md).

## Roles and permissions

Roles and permissions are data, never Python enums. Permissions follow
`<resource>.<action>` (`documents.read`, `scene.approve`) without a hard-coded
resource catalog.

```python
from authkit.authorization import Permission, Role

await backend.rbac.create_role(Role(name="reviewer"))
await backend.rbac.create_permission(Permission(name="documents.read"))
await backend.rbac.assign_permission_to_role("reviewer", "documents.read")
await backend.rbac.assign_role_to_user(user_id, "reviewer")
```

Use `auth.require_role("reviewer")` and
`auth.require_permission("documents.read")`. Permissions are placed in the
existing JWT `scopes` claim, so scopes and permissions are one mechanism:
`require_scopes` remains available for AuthWarden-compatible terminology.

## Safe administration bootstrap

The management router is disabled by default. When
`enable_admin_router=True`, every management endpoint requires a freshly loaded
user with `is_superuser=True`.

```bash
export AUTHKIT_SECRET_KEY='replace-with-at-least-32-random-bytes'
authkit create-admin --email admin@example.com
```

AuthKit never promotes the first registered user. Existing identities are
refused unless the operator explicitly passes `--promote-existing`.

## OAuth and MFA

Configure OAuth providers explicitly with `OAuthProviderConfig`; an empty
mapping means OAuth-disabled startup. PKCE/state, account linking, provider
token encryption, and Apple-specific verification remain built in. Set
`enable_mfa=True` to enable TOTP setup/confirmation/disable and hashed,
single-use backup codes. Details: [OAuth](docs/oauth.md) and [MFA](docs/mfa.md).

## Custom persistence and modular monoliths

Custom backends implement the ports exposed by `AuthBackend`; authentication
flows never import SQLAlchemy. Business modules should use `AuthUser` and
`auth.gateway.get_user(user_id)`, not adapter ORM models.

Keep business profiles in application-owned tables referencing the AuthKit user
ID:

```text
authkit_users.id  <--  application_customer_profiles.authkit_user_id
```

Do not add patient, student, company, subscription, or other domain fields to
AuthKit identity tables. See [extension guidance](docs/extending.md) and the
[modular-monolith example](examples/modular_monolith/).

## Frontend packages (optional)

```bash
pnpm add @authkit/client @authkit/react @authkit/nextjs
pnpm dlx @authkit/cli init --framework nextjs
```

Or from this repository: `authkit ui init --framework nextjs`. Generated pages
(` /login`, `/register`, …) become source in the consuming app so you can
change branding and layout without forking AuthKit. A Vite React SPA can use
`@authkit/client` + `@authkit/react` without Next.js. See
[full-stack guide](docs/full-stack.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Quickstart](docs/quickstart.md)
- [Configuration](docs/configuration.md)
- [Authentication](docs/authentication.md)
- [Authorization](docs/authorization.md)
- [SQLAlchemy adapter](docs/sqlalchemy.md)
- [Migrations](docs/migrations.md)
- [OAuth](docs/oauth.md)
- [MFA](docs/mfa.md)
- [Modular monolith](docs/modular-monolith.md)
- [Extending](docs/extending.md)
- [Security](docs/security.md)
- [Upstream audit](docs/upstream-audit.md)
- [Final report](docs/final-report.md)
- [Full-stack / UI](docs/full-stack.md)

## Development

For the full-stack example, the shortest local workflow is:

```bash
make setup
make dev
```

Useful shortcuts include `make backend`, `make frontend`, `make test`,
`make check`, `make e2e`, and `make build`. Override `BACKEND_PORT`,
`FRONTEND_PORT`, or `AUTHKIT_API_URL` when the local defaults are occupied.
The server targets release their configured TCP ports before starting; you can
also do this explicitly with `make free-port PORT=8000`.

```bash
uv sync --all-extras
uv run pytest
uv run ruff check authkit tests
uv run mypy authkit
uv build
```

PostgreSQL tests use `AUTHKIT_TEST_POSTGRES_URL`. CI starts a real PostgreSQL 16
service; fast tests remain independent of it.

## License

MIT. AuthKit preserves AuthWarden attribution and documents reference-project
usage in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
