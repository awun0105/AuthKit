# Security

This is a behavior description and deployment checklist, not a claim that every
consumer configuration is production-safe.

## Passwords and account attacks

Argon2 is the default; bcrypt is optional. Login uses `verify_and_update` so
outdated hashes are upgraded. Unknown users still trigger dummy password
verification to reduce timing-based enumeration. Login lockout and OTP attempt
limits are enabled by default. Password-reset and resend-verification HTTP
responses do not disclose account existence.

## Access and refresh lifecycle

Access/refresh JWTs validate signature, expiry, required claims, and type. Each
has a random JTI; access tokens are short-lived. Official durable backends store
only refresh JTI/family/expiry/revocation metadata—never raw tokens.

Rotation atomically consumes the presented refresh JTI and inserts its
replacement. Replay of an already-consumed JTI revokes the entire family.
Logout revokes bearer/refresh JTIs and deletes the linked session. Password
change/reset revoke every persisted refresh and session for the user.

Login records the request User-Agent and a SHA-256 hash of the client IP
(preferring `X-Forwarded-For`) on the session. Raw IPs are not stored.

Browser mode stores the access token in memory and the refresh token in a
Secure-by-default, HttpOnly, appropriately SameSite cookie. Refresh/logout requests must
carry `X-AuthKit-Requested-With: AuthKit`; cross-site HTML forms cannot add
that header. SameSite is defense in depth rather than the only CSRF control.
The default JSON/bearer transport remains available for API/mobile clients and
is not automatically sent cross-site. Production cookie deployments must use
TLS, `refresh_cookie_secure=True`, exact CORS origins, and
`allow_credentials=True`; never combine credentialed CORS with `*`.
`SameSite=None` is rejected unless `Secure` is also enabled. Local HTTP
examples must explicitly opt out of `Secure`; production must not.

## Verification and reset tokens

Signed link tokens have purpose-specific salts and expiry. Only SHA-256 hashes
are persisted and comparisons are constant-time. Reset link tokens track
single-use state. Numeric OTPs are hashed, expire, and invalidate at the attempt
limit.

## OAuth and MFA

OAuth authorization uses random, expiring, atomically consumed state plus S256
PKCE. State is provider/purpose-bound and account-connect state is user-bound.
An authorize request carrying an invalid bearer token fails; it is never
downgraded from account-connect intent into a public login state.
Provider identity is keyed by provider user ID, not trusted email alone.
Provider tokens are Fernet-encrypted at rest and absent from public DTOs.

TOTP secrets are pending until confirmed. Backup codes are shown once, stored
as password hashes, and consumed once. MFA remains opt-in.

## Authorization and bootstrap

Roles/permissions are consumer data. The admin router is disabled by default;
when enabled it requires freshly loaded `is_superuser` state. Never expose it
without normal network/rate-limit controls. `authkit create-admin` is explicit,
never promotes the first registrant, and refuses existing users unless
`--promote-existing` is provided.

Role/permission changes appear in new/rotated JWTs. Use short access TTLs when
rapid permission removal matters. Disabled users are rejected immediately by
`current_user` even while a token remains cryptographically valid.

## Deployment checklist

- Use TLS and a random secret of at least 32 bytes from a secret manager.
- Run packaged migrations before starting traffic.
- Use PostgreSQL and shared persistence for multi-process revocation/state.
- Rate-limit public auth endpoints at a proxy/API gateway as well as per user.
- Configure exact OAuth redirect URIs and production provider credentials.
- Protect database backups because they contain password hashes, MFA secrets,
  encrypted OAuth tokens, and security audit data.
- Retain audit data according to policy; application logs and audit rows are
  intentionally separate.
