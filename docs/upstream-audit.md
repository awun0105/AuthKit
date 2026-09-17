# Upstream AuthWarden audit

Audit date: 2026-09-18

This document records the repository baseline before the AuthKit rename and
architecture work. It distinguishes behavior verified in source/tests from
claims made in the upstream documentation.

## Repository and history baseline

- The working repository is `AuthKit/` on branch `feat/authkit-foundation`.
- `HEAD` is `fc5d817` (`Initial commit`). At audit time Git tracked only
  `.gitignore`, `LICENSE`, and the one-line `README.md`; the imported AuthWarden
  source, tests, documentation, and packaging files were present but untracked.
- The source snapshot identifies its upstream as
  `https://github.com/timihack/authwarden` and its package version as `1.0.0`.
- The two reference repositories were clean and were inspected read-only:
  `vishwap-bp/fastapi-auth-rbac` at `9bf9e84` and
  `arctikant/fastapi-modular-monolith-starter-kit` at `9d30883`.
- No `CHANGELOG`, `NOTICE`, or third-party notices file was present. The current
  `LICENSE` names the AuthKit repository owner, while the imported upstream
  README attributes AuthWarden to `timihack`. AuthKit must retain both the
  project's own license notice and the required upstream attribution.

## Baseline validation

Commands were run from `AuthKit/` with Python 3.11.14:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q authwarden tests
UV_CACHE_DIR=/tmp/authkit-uv-cache uv build
```

Results:

- `pytest`: **390 passed**, 123 warnings, in 41.79 seconds.
- `compileall`: passed.
- package build: produced `authwarden-1.0.0.tar.gz` and
  `authwarden-1.0.0-py3-none-any.whl` successfully.
- No Ruff or mypy configuration existed. `pyproject.toml` configured only
  pytest (`asyncio_mode = "auto"`, `testpaths = ["tests"]`).
- Warnings included short HMAC keys used by tests, plus Authlib/Starlette
  deprecations. The short test keys are not acceptable production examples.

## Current architecture

AuthWarden is an async, protocol-oriented FastAPI library:

```text
AuthWarden facade
  -> router builders and FastAPI dependencies
  -> authentication/application flows
  -> Pydantic identity/token models and security utilities
  -> user/session/notification/OAuth-state/token-blacklist protocols
  -> in-memory, Redis, email, and SMS implementations
```

The authentication flows do not import an ORM. Persistence is reached through
`AbstractUserStore`; optional sessions, OAuth state, token revocation, and
notifications have separate contracts. Router functions close over a single
facade instance's configuration and dependencies, avoiding module-global app
state and import-time database connections.

## Current public API

`authwarden.__init__` explicitly exports:

- `AuthWarden`, `WardenConfig`, `OAuthProviderConfig`
- `AuthError`
- `UserCreate`, `UserRead`, `UserInDB`
- `OAuthAccount`, `OAuthAccountRead`, `OAuthUserInfo`
- `TokenPair`, `TokenPayload`, `RefreshTokenRequest`, `LogoutRequest`
- `AbstractUserStore`, `MemoryUserStore`

The facade exposes:

- `warden.router`
- `warden.current_user`
- `warden.require_roles(*roles, require_all=False)`
- `warden.require_scopes(*scopes, require_all=False)`
- advanced access through `store`, `password_handler`, `jwt_handler`,
  `session_backend`, `notification_service`, `oauth_state_store`, and
  `oauth_providers`

## Current protocols and storage abstractions

The source defines these runtime-checkable protocols:

- `AbstractUserStore`: async user CRUD, lookup by ID/email/username/phone, and
  OAuth-account CRUD.
- `AbstractSessionBackend`: create/get/delete sessions, delete all sessions for
  a user, and list a user's active sessions.
- `AbstractTokenBlacklist`: add/check revoked JWT IDs with TTL.
- `AbstractOAuthStateStore`: create and atomically consume OAuth state.
- `AbstractNotificationService`: verification, welcome, password, and MFA
  notification operations.
- `AbstractEmailBackend` and `AbstractSmsBackend`: transport-specific send
  operations.

Provided storage implementations are `MemoryUserStore`,
`MemorySessionBackend`, `RedisSessionBackend`, `MemoryTokenBlacklist`,
`RedisTokenBlacklist`, and `MemoryOAuthStateStore`. There is no official
database adapter, database-backed OAuth-state store, persistent token
blacklist, audit sink, or persistent RBAC store.

## Authentication flows

Verified source flows include:

- registration with email/username/phone uniqueness checks and configurable
  link or OTP verification;
- login using configured identifier priority, dummy password verification,
  account lockout, optional email verification, optional TOTP, silent password
  rehash, JWT issuance, and optional session creation;
- logout by access-token revocation and optional refresh-token revocation;
- refresh-token verification and optional one-time rotation;
- authenticated password change and OAuth-only account password setup;
- password reset by signed link or OTP;
- email/account verification by signed link or OTP;
- resend cooldown and anti-enumerating response behavior.

`allow_registration` exists in configuration but the audited router/flow does
not enforce it.

## Token and refresh lifecycle

- PyJWT signs HS256 access and refresh JWTs by default.
- Each token has `sub`, random `jti`, `type`, `roles`, `scopes`, `iat`, and
  `exp`; token type is enforced during decode.
- `verify_token` checks signature, expiry, claims/type, and a pluggable JTI
  blacklist.
- Refresh rotation blacklists the submitted refresh JTI before issuing a new
  pair. Logout always blacklists the access JTI and best-effort blacklists a
  submitted refresh token.
- Default blacklist state is process-local memory. Redis can be supplied for
  shared revocation state.
- There is no refresh-token family identifier or family-wide replay response.
  Rotation rejects replay of the exact revoked JTI only when blacklist state
  is available and shared.
- Password change/reset does not currently revoke all existing refresh tokens
  or sessions. The change-password flow issues a fresh pair.

## OAuth flow

- Eight providers are implemented: Google, GitHub, Facebook, Microsoft,
  LinkedIn, Discord, Twitter/X, and Apple.
- OAuth is config-driven; an empty provider mapping starts without provider
  credentials.
- Every authorization request uses S256 PKCE and random single-use state.
  State records provider, purpose (`login`/`connect`), and user ID for connect.
- Callback consumes state before code exchange, validates purpose/provider,
  normalizes provider user data, and links by authoritative provider user ID.
- Optional email auto-linking is supported; otherwise matching email raises an
  explicit conflict.
- Provider access/refresh tokens are Fernet-encrypted before persistence.
- Disconnect prevents removal of the final login method.
- Apple implements dynamically signed client secrets and verified `id_token`
  handling with a cached JWKS client.

## MFA flow

- MFA is disabled by default.
- TOTP setup stores a pending secret, confirmation activates it, and disable
  requires password plus a valid TOTP code.
- Backup codes are generated once, stored as password hashes, and consumed
  once.
- OTP verification/reset attempt limits invalidate the OTP on the configured
  threshold.
- The login flow accepts TOTP; backup-code login is implemented/tested at flow
  level where applicable and must remain covered during refactoring.

## Authorization behavior

- Roles and arbitrary scopes are lists on `UserInDB` and are copied into JWTs.
- Role/scope dependencies authorize from token claims, so changes take effect
  on the next token issuance/refresh rather than immediately.
- `current_user` additionally fetches the user and rejects a missing or
  inactive account on each request.
- `require_roles` and `require_scopes` support any/all matching.
- A built-in role hierarchy hard-codes `guest`, `user`, `moderator`, `admin`,
  and `superadmin`; this is not suitable as AuthKit's database-backed generic
  role source.
- Scopes are the existing permission-like claim. AuthKit should retain the
  claim for compatibility and map database permissions to it, rather than add
  an unrelated third authorization vocabulary.

## Router construction

`AuthWarden` constructs one combined `APIRouter` from auth, MFA, and OAuth
router builders. Optional features still contribute routes; feature/config
checks happen in the flows. The router covers register, verification, login,
logout, refresh, password flows, MFA management, OAuth authorization/callback,
and OAuth account management.

The login router does not pass request/user-agent/IP information into session
creation. A session is created when enabled, but its ID is not returned or
embedded in issued tokens. The logout router does not pass the configured
session backend or a session ID to `logout_flow`, so device-session deletion is
not currently reachable through the stock HTTP endpoint.

## Optional dependencies and Redis

Base dependencies currently include FastAPI, Pydantic/settings, pwdlib with
Argon2/bcrypt, PyJWT, itsdangerous, pyotp, Authlib, HTTPX, cryptography,
aiosmtplib, and multipart parsing. Extras are:

- `sns`: boto3
- `redis`: redis
- `all`: boto3 and redis
- `dev`: pytest, pytest-asyncio, respx, boto3, redis

Redis is used only for optional session storage and an explicitly constructed
token blacklist. Redis key prefixes are currently `authwarden:*` and require a
rename/compatibility decision.

## Security-sensitive utilities and invariants

The following verified properties must not regress:

- Argon2 is the default password hasher; bcrypt remains selectable.
- Login performs a dummy hash verification for unknown/no-password users.
- Account lockout and OTP attempt limiting are enabled by default.
- Password reset and resend endpoints use non-enumerating HTTP messages.
- OTP/reset/verification secrets are stored as SHA-256 hashes and compared in
  constant time; raw single-use flow tokens are not stored.
- Link tokens use purpose-specific itsdangerous salts and expiry.
- JWT signature, expiry, type, and revocation are validated.
- OAuth uses state plus PKCE; state is atomically single-use.
- OAuth provider tokens are encrypted at rest and absent from public DTOs.
- Backup codes are hashed and single-use.
- Current-user resolution rechecks active status from storage.
- Bearer tokens are returned in response bodies, not automatically attached
  cookies; cookie integrations require consumer-managed CSRF defenses.

## Extension points

Existing extension points are the protocols above, custom Pydantic user/read
models, custom password handler, notification service/templates, email/SMS
backends, token blacklist, session backend, OAuth state store, and configured
OAuth providers. The facade is already a useful composition root and should be
evolved rather than replaced wholesale.

## Existing test coverage

The 390 tests cover:

- Pydantic models, exceptions, utilities, config, and memory stores;
- password hashing/policy, JWT creation/validation/revocation, sessions;
- registration, verification, login/lockout, logout, refresh, password flows,
  notification routing, and storage substitution;
- OTP limits, TOTP setup/confirm/disable, backup codes, roles, and scopes;
- PKCE, encryption, OAuth state, provider URLs/userinfo normalization, OAuth
  callback/link/disconnect, Apple behavior, and OAuth password setup;
- facade/router assembly and FastAPI HTTP behavior across auth, MFA, and OAuth.

Not covered by the upstream suite: SQLAlchemy, PostgreSQL, Alembic, persistent
RBAC, audit persistence, CLI behavior, clean-install consumer integration,
static typing, or a real Redis/PostgreSQL service.

## Known limitations and missing AuthKit pieces

1. Package/facade/config names and imports are still AuthWarden-specific.
2. Configuration auto-loads a global `.env`; AuthKit needs explicit config by
   default with opt-in environment loading.
3. No official SQLAlchemy async adapter, PostgreSQL integration, or packaged
   migrations exist.
4. RBAC is embedded list data with a hard-coded optional hierarchy; there are
   no role/permission entities, assignment store, or administration endpoints.
5. Scopes have no documented `<resource>.<action>` convention.
6. No audit protocol or audit persistence exists.
7. Session records are not fully connected to token issuance/logout at the
   stock router boundary.
8. Refresh rotation has no persistent token-family replay detection.
9. Password reset/change does not revoke all prior sessions by default.
10. There is no admin bootstrap command or isolated migration CLI.
11. There is no public DTO/gateway/event surface for modular monoliths.
12. No runnable minimal, PostgreSQL, or modular-monolith example applications
    are packaged.
13. Public/internal exports need consolidation and `__all__` coverage.
14. The facade computes a default email backend but passes the original
    constructor argument into `NotificationService`; when no backend is passed,
    the default console transport is therefore not actually wired. This is a
    concrete bug to fix with regression coverage after the rename baseline.
15. Upstream attribution and third-party usage records need to be formalized.

## Reference-pattern decisions

The RBAC reference demonstrates relational user-role and role-permission join
tables, unique role/permission identifiers, refresh/session persistence,
append-only audit rows, and Alembic metadata registration. Its synchronous ORM,
JWT/password implementation, generic table names, colon permission syntax, and
application-global settings are not suitable for direct reuse.

The modular-monolith reference demonstrates a narrow `AuthGatewayInterface`,
public `UserDTO`, FastAPI `Annotated` dependencies, meaningful user lifecycle
events, and explicit `__all__`. AuthKit should adapt those boundary concepts
without importing its ORM models, service container, or event provider.

No reference source code had been transplanted at this audit point.
