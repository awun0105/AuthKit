# API Reference

The base router exposes 20 authentication/MFA/OAuth endpoints. The optional
admin router adds management endpoints only when explicitly enabled.

## Auth

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/register` | No | Registration |
| POST | `/verify-email` | No | Verification — link mode |
| POST | `/verify-otp` | No | Verification — OTP mode |
| POST | `/resend-verification` | No | Resend verification |
| POST | `/login` | No | Login |
| POST | `/logout` | Yes | Logout and revoke |
| POST | `/refresh` | No¹ | Rotate refresh token |
| POST | `/forgot-password` | No | Request reset |
| POST | `/reset-password` | No | Reset — link mode |
| POST | `/reset-password-otp` | No | Reset — OTP mode |
| POST | `/change-password` | Yes | Change and revoke old sessions |
| POST | `/set-password` | Yes | Set password on OAuth-only account |

¹ Authenticated implicitly via the refresh token in the request body, not a Bearer header.

## MFA (`/mfa` prefix)

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/mfa/setup` | Yes | [MFA](mfa.md) |
| POST | `/mfa/confirm` | Yes | [MFA](mfa.md) |
| POST | `/mfa/disable` | Yes | [MFA](mfa.md) |

## OAuth (`/oauth` prefix)

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/oauth/accounts` | Yes | [Account linking](oauth/account-linking.md) |
| GET | `/oauth/{provider}/authorize` | Optional² | [OAuth](oauth.md) |
| POST | `/oauth/{provider}/callback` | No | [OAuth](oauth.md) |
| POST | `/oauth/{provider}/connect` | Yes | [OAuth](oauth.md) |
| DELETE | `/oauth/{provider}/disconnect` | Yes | [OAuth](oauth.md) |

² A valid bearer changes authorize from login to account-connect mode.

## Optional administration (`/admin` prefix)

Superuser authentication is required for role/permission create/list/delete,
role-permission assignment/removal, and user-role assignment/removal. See
[authorization](authorization.md).

## Authentication header

Every authenticated endpoint expects:

```
Authorization: Bearer <access_token>
```

## Exception → status code reference

Every flow raises a typed `AuthError` subclass; the router converts it to the matching `HTTPException` automatically.

| Exception | Status | | Exception | Status |
|---|---|---|---|---|
| `EmailAlreadyExists` | 409 | | `InvalidToken` | 400 |
| `UsernameAlreadyExists` | 409 | | `TokenExpired` | 400 |
| `PhoneAlreadyExists` | 409 | | `TokenRevoked` | 401 |
| `WeakPassword` | 422 | | `TokenAlreadyUsed` | 400 |
| `InvalidEmail` | 422 | | `SamePassword` | 422 |
| `AlreadyVerified` | 409 | | `PasswordNotSet` | 400 |
| `RateLimited` | 429 | | `PasswordAlreadySet` | 400 |
| `InvalidCredentials` | 401 | | `UserNotFound` | 404 |
| `AccountInactive` | 403 | | `ForbiddenError` | 403 |
| `AccountLocked` | 403 | | `MFANotEnabled` | 400 |
| `EmailNotVerified` | 403 | | `MFAAlreadyEnabled` | 409 |
| `InvalidMFACode` | 401 | | `InvalidBackupCode` | 401 |
| `MFARequired` | 403 | | `OAuthProviderNotConfigured` | 404 |
| `OAuthStateMismatch` | 400 | | `EmailAlreadyRegistered` | 409 |
| `OAuthCodeExchangeFailed` | 502 | | `ProviderAlreadyLinked` | 409 |
| `OAuthUserInfoFailed` | 502 | | `LastLoginMethod` | 400 |
| `OAuthAccountNotFound` | 404 | | | |

Every response body follows FastAPI's standard error shape:

```json
{ "detail": "human-readable message" }
```
