# OAuth

OAuth is optional at runtime: leave `oauth_providers={}`. Configured providers
use S256 PKCE plus random, expiring, single-use state. Login state and account-
connect state are purpose-bound; connect state is user-bound.

Account resolution uses provider plus provider-user ID as the authoritative
key. Email auto-linking is configurable. Provider access/refresh tokens are
Fernet-encrypted before storage and excluded from public DTOs. Disconnecting
the last login method is rejected.

Never reuse development redirect URIs or secrets in production. Require HTTPS
and register exact callback URLs at each provider.

See [Apple Sign In](oauth/apple.md) and [account linking](oauth/account-linking.md)
for provider-specific details retained from the upstream implementation.
