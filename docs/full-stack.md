# Full-stack AuthKit

AuthKit is a reusable authentication foundation. The Python package is
backend-only. Optional frontend packages add a typed HTTP client, React
session state, Next.js helpers, and **source-owned** UI you copy into your app.

## Backend-only

```bash
uv add "authkit[postgres]"
authkit db upgrade
```

Mount `auth.router`. No Node install is required.

## FastAPI + Next.js

1. Install and configure Python AuthKit; run migrations; mount the router.
2. Enable browser cookies if the UI and API share a site:

   ```python
   AuthKitConfig(..., enable_refresh_cookie=True, refresh_cookie_secure=True)
   ```

3. CORS must list the exact frontend origin with `allow_credentials=True`.
   Do not use `*` with cookies.
4. In the Next.js app:

   ```bash
   pnpm add @authkit/client @authkit/react @authkit/nextjs
   pnpm dlx @authkit/cli init --framework nextjs
   ```

   Or from this repo: `authkit ui init --framework nextjs --dir .`

5. Set `NEXT_PUBLIC_AUTHKIT_API_URL` (default `http://localhost:8000/auth`).
6. Run backend and `pnpm dev`, then register at `/register`.

The scaffold also adds Tailwind CSS 4 and its PostCSS plugin when they are not
already present. Existing dependency versions and existing source files are
preserved unless `--force` is explicitly supplied.

## Packages

| Package | Use |
|---|---|
| `@authkit/client` | Typed HTTP API, refresh lock, `AuthKitError` |
| `@authkit/react` | `AuthProvider`, `useAuth`, UX guards |
| `@authkit/nextjs` | middleware redirects, OAuth callback helper |
| `@authkit/cli` | copies UI source into the consumer app |

Small public surfaces:

```ts
// @authkit/client
createAuthClient, AuthKitClient, AuthKitError

// @authkit/react
AuthProvider, useAuth, RequireAuth, RequireRole, RequirePermission

// @authkit/nextjs
authkitMiddleware, safeLocalRedirect, completeOAuthCallback
```

`useAuth()` exposes `user`, `isAuthenticated`, `isLoading`, and a structured
`error` alongside the auth actions. A startup `NETWORK_ERROR` is surfaced
without erasing a potentially valid in-memory session.

For authenticated business endpoints, use the client's public
`client.request(path, init, { auth: true })` escape hatch. It attaches the
current access token and applies the same single-flight refresh/retry behavior
as the built-in AuthKit calls; the backend remains the authorization authority.

A Vite React SPA can use client + react only. A custom UI can use client only.

Types are hand-written to match the backend HTTP contracts (see
[api-reference](api-reference.md)). OpenAPI codegen was skipped to keep the
developer workflow simple and deterministic.

## Customization

Generated files live in your repo (`app/(auth)/`, `components/auth/`,
`lib/auth/`). Change logo and `appName` in `lib/auth/config.ts`, colors in
`app/globals.css` (`--auth-*` variables), then edit any component.

Customization is deliberately layered:

1. Set `appName`, `logo`, API URL, and post-login redirect in
   `lib/auth/config.ts`.
2. Change CSS variables or Tailwind utilities for colors, spacing, and dark
   mode.
3. Compose or replace an individual generated form.
4. Edit any generated page directly; it is consumer-owned source.
5. Ignore the templates entirely and use only the client or React package.

For example, scaffold the default login, replace the logo, change the
Tailwind layout, and add project-specific links while leaving `useAuth().login`
unchanged.

Frontend `hasRole` / `RequirePermission` are UX only. The API still enforces
RBAC.

## Session model

- Access token: short-lived, Authorization Bearer, memory in the browser client.
- Refresh token: JSON body for API/mobile (`mode: "bearer"`), or HttpOnly
  `authkit_refresh` cookie when `enable_refresh_cookie=True`.
- Browser client sends `X-AuthKit-Requested-With: AuthKit` on cookie mutations
  so cross-site form posts cannot refresh/logout.
- `authkit_authenticated=1` is a non-secret flag for Next.js middleware
  redirects, not a security boundary. Its default seven-day `Max-Age` can be
  changed with `authenticatedCookieMaxAge`; align it with the backend refresh
  TTL.
- `SameSite=Lax` is defense in depth, not the only CSRF control. Production
  cookie mode also requires HTTPS, `refresh_cookie_secure=True`, exact CORS
  origins, and `allow_credentials=True`.

OAuth buttons are derived from `GET /config`. Account linking records a
short-lived connect purpose in `sessionStorage`, restores the cookie-backed
session after the provider redirect, and completes through the backend's
single-use OAuth state. MFA setup/disable controls are rendered only when
`enable_mfa` is advertised by the backend.

Keep business profiles in your own tables keyed by AuthKit user id. Fetch
`DoctorProfile`, `CustomerProfile`, or other domain data from the application
API rather than adding those fields to `AuthUser`.
