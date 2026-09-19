# AuthKit V1 final report

This is the completion record for turning the AuthWarden snapshot in this
workspace into AuthKit. It is a library report, not a claim that every
consumer deployment is production-safe.

## A. Architecture

Dependency direction is inward:

```text
FastAPI facade / CLI
        |
        v
flows + authorization + gateway + events
        |
        v
Pydantic models and Protocol ports
        ^
        |
memory / SQLAlchemy / Redis / consumer adapters
```

`AuthKit` is a composition root. It accepts either a bundled `AuthBackend` or
a custom `user_store`, then builds instance-local routers and dependencies.
Core flows never import SQLAlchemy. The official SQLAlchemy adapter implements
the same ports as the memory backend: users, RBAC, sessions, refresh families,
token revocation, OAuth state, and audit.

Package layout keeps the existing AuthWarden flow/router/security modules and
adds `adapters/`, `authorization/`, `gateway.py`, `events.py`, `audit.py`,
`migrations.py`, and `cli.py` rather than rewriting the tree for its own sake.

## B. What was reused

Retained from AuthWarden, renamed into the `authkit` namespace:

- Registration, login, logout, refresh, password, and verification flows
- JWT access/refresh handling, password hashing (Argon2 default, bcrypt option)
- OAuth providers, PKCE, state, account linking, encrypted provider tokens
- MFA/TOTP, hashed backup codes, lockout, OTP attempt limits, anti-enumeration
- Notification protocols and email/SMS backends
- In-memory and Redis session/blacklist stores
- FastAPI router builders and `current_user` / role / scope dependencies
- Upstream test phases 1–7 (package names updated)

## C. What was added

- `AuthKit` / `AuthKitConfig` public facade, with `backend=` as the official
  integration path
- Official `MemoryBackend` and `SQLAlchemyBackend`
- Isolated Alembic history (`authkit_alembic_version`) and `authkit db` CLI
- Generic DB-backed roles/permissions and optional superuser admin router
- `authkit create-admin` (never auto-promotes the first registrant)
- Audit sink protocol plus SQLAlchemy/memory sinks
- In-process events and `AuthGateway` / `AuthUser`
- Packaged examples, rewritten docs, GitHub Actions PostgreSQL CI
- Full-stack workspace packages: `@authkit/client`, `@authkit/react`,
  `@authkit/nextjs`, and source-owned Next.js UI scaffolding via
  `@authkit/cli`
- Public-API e2e coverage and a clean-install consumer smoke test

## D. Reference repository usage

Both reference repositories were inspected read-only. No files, folders, or
git history were copied.

- `reference-fastapi-auth-rbac`: relational user-role / role-permission tables,
  namespaced AuthKit tables, append-only audit rows, refresh persistence, and
  Alembic isolation. Its JWT/password stack and generic `users` table names
  were not reused.
- `reference-modular-monolith`: public DTO, gateway lookup, in-process
  lifecycle events, and explicit `__all__`. Its ORM models, container, and
  broker were not reused.

## E. Security review

Verified in source and covered by the retained plus new tests:

- Argon2 default hashing with dummy verification for unknown users
- Lockout and OTP attempt limiting
- Non-enumerating reset/resend HTTP responses
- Hashed single-use reset/verification secrets; purpose-specific signed links
- JWT signature, expiry, type, and JTI revocation checks
- Refresh rotation with family-wide replay revocation on durable backends
- Logout revokes access/refresh JTIs and the linked session
- Password change/reset revoke persisted refresh tokens and sessions
- OAuth PKCE + single-use state; provider tokens encrypted at rest
- Backup codes hashed and single-use
- `current_user` reloads storage and rejects inactive users
- Admin router disabled by default; enabled routes require `is_superuser`
- `secret_key` must be at least 32 bytes
- Login stores User-Agent and a hashed client IP on the session

This is not a guarantee that a misconfigured consumer deployment is safe.

## F. Breaking changes from AuthWarden

- Package, facade, and config names: `authwarden` / `AuthWarden` /
  `WardenConfig` → `authkit` / `AuthKit` / `AuthKitConfig`
- Redis key prefixes: `authwarden:*` → `authkit:*`
- Configuration no longer auto-loads a global `.env`; use
  `AuthKitConfig.from_env()` explicitly
- `AuthKit(...)` requires `backend=` or `user_store=`
- Official SQLAlchemy tables are `authkit_*`, not generic application names
- Optional admin router and CLI are new and off by default

No compatibility import shim (`import authwarden`) is provided.

## G. Public API

```python
from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend
from authkit.adapters.sqlalchemy import SQLAlchemyBackend

backend = SQLAlchemyBackend(database_url=settings.database_url)
auth = AuthKit(
    config=AuthKitConfig(secret_key=settings.auth_secret),
    backend=backend,
)
app.include_router(auth.router, prefix="/auth")

user = Depends(auth.current_user)
Depends(auth.require_role("reviewer"))
Depends(auth.require_permission("documents.create"))
identity = await auth.gateway.get_user(user_id)
```

```bash
uv add "authkit[postgres]"
authkit db upgrade
authkit create-admin --email admin@example.com
```

Advanced customization still uses protocols (`AbstractUserStore`, `RBACStore`,
`AuditSink`, `EventSink`) rather than adapter ORM internals.

## H. Database schema

AuthKit-owned tables:

| Table | Purpose |
|---|---|
| `authkit_users` | Minimal identity |
| `authkit_oauth_accounts` | Linked providers |
| `authkit_roles` | Consumer-defined roles |
| `authkit_permissions` | `<resource>.<action>` permissions |
| `authkit_user_roles` | User ↔ role |
| `authkit_role_permissions` | Role ↔ permission |
| `authkit_sessions` | Device sessions |
| `authkit_refresh_tokens` | Refresh JTI/family metadata |
| `authkit_token_revocations` | Access/refresh JTI blacklist |
| `authkit_oauth_states` | Single-use OAuth state |
| `authkit_audit_events` | Optional security audit |
| `authkit_alembic_version` | Isolated migration metadata |

Relationships: User → UserRole → Role → RolePermission → Permission. OAuth
accounts, sessions, and refresh rows belong to a user. Raw refresh tokens are
not stored.

## I. Validation

Ran from this workspace on 2026-09-19 (Python 3.11.14).

```text
.venv/bin/ruff check authkit tests
  All checks passed

.venv/bin/mypy --config-file pyproject.toml authkit
  Success: no issues found in 91 source files

.venv/bin/pytest -m "not postgres" -q
  406 passed, 1 deselected, 3 warnings

.venv/bin/pytest -m postgres -q
  1 passed, 406 deselected, 3 warnings

pnpm test
  client 9 passed; react 4 passed; nextjs 3 passed; cli 4 passed

pnpm lint && pnpm typecheck && pnpm build
  ESLint, React Hooks rules, TypeScript, and all four package builds passed

uv build
  dist/authkit-1.0.0.tar.gz
  dist/authkit-1.0.0-py3-none-any.whl
```

The 406 passing tests include the preserved AuthWarden phase suite, SQLAlchemy
migration/RBAC/admin/CLI coverage, a public-API e2e flow, and a clean-install
consumer smoke test that installs `authkit[sqlalchemy]` into a temporary venv
and exercises register → login → me → permission → refresh → logout without
importing ORM internals. The PostgreSQL marker passed against a local PostgreSQL
16 container. The full-stack Playwright suite starts both servers and passed
three browser flows, including expiry-driven refresh-cookie restoration and
rendering every public authentication page.

## J. Remaining limitations

- This workspace's Git history starts at a single `Initial commit`. Useful
  AuthWarden commit history was not present to preserve.
- `UserDisabled` / `UserDeleted` events are not emitted; there is no first-class
  disable/delete identity API in V1.
- The retained JWT role ladder (`guest`…`superadmin`) still exists for
  `has_min_role` compatibility. It is not the DB RBAC catalog.
- OAuth libraries remain in the base extra set because they were already core
  AuthWarden dependencies; there is no separate `authkit[oauth]` extra.
- V1 does not include multi-tenancy, SAML, an OIDC authorization server, ABAC,
  ReBAC, or a policy DSL.
- The default UI is a source scaffold, not a general design system. Consumers
  remain responsible for production CORS/origin policy and setting Secure
  cookies outside localhost.
- PostgreSQL tests require `AUTHKIT_TEST_POSTGRES_URL` (provided in CI).
- Package publication was not performed. Clean temporary consumers installed
  the final local wheel and JavaScript tarballs instead.
- Live OAuth provider acceptance still requires consumer-owned provider
  credentials and registered redirect URIs; CI verifies state/PKCE/callback
  contracts with mocked providers.
- The current Authlib/FastAPI dependency set emits upstream deprecation
  warnings about their transitional httpx integrations; validation passes,
  but those warnings should be revisited when upstream dependency migrations
  stabilize.
