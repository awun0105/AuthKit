# Frontend contract baseline

Recorded against AuthKit backend on branch `feat/authkit-ui` after the
backend-only suite: **403 passed**, 1 postgres test deselected.

Authoritative HTTP surface (router prefix typically `/auth`):

- POST `/register`, `/login`, `/logout`, `/refresh`
- POST `/verify-email`, `/verify-otp`, `/resend-verification`
- POST `/forgot-password`, `/reset-password`, `/reset-password-otp`
- POST `/change-password`, `/set-password`
- POST `/mfa/setup`, `/mfa/confirm`, `/mfa/disable`
- GET/POST/DELETE `/oauth/...`
- Additive frontend-support endpoints: GET `/config`, GET `/me`, GET `/sessions`,
  GET `/oauth/providers`

Error bodies remain `{ "detail": "..." }`. Structured codes are also sent as
`X-AuthKit-Error` without changing the JSON shape.
