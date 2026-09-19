# Full-stack AuthKit report

## A. Repository structure

Python backend remains at the repository root (`authkit/`). Frontend packages
live beside it so Git history is not rewritten:

```text
authkit/                  # Python library
packages/client           # @authkit/client
packages/react            # @authkit/react
packages/nextjs           # @authkit/nextjs
packages/cli              # @authkit/cli + Next.js templates
examples/fullstack-nextjs
examples/minimal          # backend-only
```

## B. Backend changes

Additive for valid existing clients:

- `GET /config`, `GET /me`, `GET /sessions`, `GET /oauth/providers`
- `X-AuthKit-Error` header on `AuthError`
- optional HttpOnly refresh cookie + CSRF header
- `RefreshTokenRequest.refresh_token` is optional so cookie refresh works
- an OAuth authorize request that supplies an invalid bearer now fails instead
  of silently creating public-login state

JSON `{ "detail": "..." }` is unchanged. Existing Bearer tests still pass.

## C. `@authkit/client`

`createAuthClient({ baseUrl, mode: "bearer" | "browser" })` with
`register`, `login`, `logout`, `refresh`, `getCurrentUser`, `restoreSession`,
password/verify/MFA/OAuth helpers, OAuth account linking, a refresh-aware
authenticated request escape hatch, and `AuthKitError`.

## D. `@authkit/react`

`AuthProvider`, `useAuth`, `RequireAuth`, `RequireRole`, `RequirePermission`.
Restores session on mount; access token lives in memory; refresh is
single-flight; startup network/account errors are exposed as structured state.

## E. `@authkit/nextjs`

`authkitMiddleware` (UX cookie flag), `safeLocalRedirect`, and
`completeOAuthCallback` for login or account-connect callbacks.

## F. UI scaffolding

```bash
pnpm dlx @authkit/cli init --framework nextjs --dir .
# or
authkit ui init --framework nextjs --dir .
```

`--dry-run` and `--force` are supported. Files are copied into the consumer
tree.

## G. Session security

Access token: Bearer, memory. Refresh: body (API) or HttpOnly cookie (browser).
Cookie mutations require `X-AuthKit-Requested-With: AuthKit`. SameSite=Lax by
default. CORS must use an explicit origin with credentials.

## H. Example

See `examples/fullstack-nextjs/README.md`.

## I. Validation

```text
pytest -m "not postgres" -q
  406 passed, 1 deselected

ruff check authkit tests
  All checks passed

pnpm lint && pnpm typecheck
  ESLint (including React Hooks) and TypeScript passed

pnpm --filter @authkit/client --filter @authkit/react --filter @authkit/nextjs --filter @authkit/cli build
  success

pnpm --filter @authkit/client --filter @authkit/react --filter @authkit/nextjs --filter @authkit/cli test
  client 9 passed; react 4 passed; nextjs 3 passed; cli 4 passed
```

PostgreSQL was exercised against the local PostgreSQL 16 container:
`1 passed, 406 deselected`. The Playwright suite starts isolated FastAPI and
Next.js servers with a two-second access-token lifetime: `3 passed` using
system Chrome. The Next.js production build and local package tarball builds
also passed. Clean temporary consumers imported client-only, `@authkit/react`
without Next.js, and full Next.js tarball installs; the installed CLI performed
both dry-run and real source scaffolding.

## J. Limitations

- No Vue/React Native packages yet (client remains usable).
- Refresh cookies default to `Secure`; localhost examples explicitly opt out
  and production deployments must not.
- Next middleware is not a security boundary.
- The middleware flag is mirrored by the browser client on the frontend host;
  the API's host-only flag is not visible to a separate Next.js origin.
- Publishing the built Python/JavaScript artifacts to PyPI or npm was not
  performed; validation used local wheel and tarball installs.
- OAuth provider redirects require real provider credentials, so provider-live
  callbacks remain an environment acceptance test rather than a CI test.
