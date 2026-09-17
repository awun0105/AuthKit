# Configuration

`AuthKitConfig(...)` is explicit and never reads `.env` or process variables.
Use `AuthKitConfig.from_env()` to opt into `AUTHKIT_*` variables; structured
values use JSON. A file is read only when passed as `env_file=...`.

Important groups:

| Area | Fields and defaults |
|---|---|
| JWT | `secret_key` required; access 900s; refresh 604800s; rotation enabled |
| Password | Argon2; minimum 8; optional upper/digit/special policies |
| Lockout | 5 failed logins; 900s lock; 5 OTP attempts |
| Verification | required; link mode; email channel; OTP 600s |
| Reset | link mode; email channel; link 3600s |
| Registration | enabled |
| Sessions | backend-provided, or legacy `memory`/`redis` selector |
| MFA | disabled; issuer `AuthKit` |
| OAuth | no providers; email auto-link enabled |
| Admin router | disabled |

```python
config = AuthKitConfig.from_env(
    env_file="/run/secrets/authkit.env",
    require_email_verification=True,
)
```

`allow_registration=False` is enforced by the registration flow. Redis
requires `redis_url`. OAuth providers are explicit `OAuthProviderConfig`
objects. SendGrid/Mailgun/Twilio/SNS or custom notification systems are passed
as backend instances rather than selected through magic global settings.

Use a random secret of at least 32 bytes from a secret manager. Development
examples are placeholders, not deployable secrets.
