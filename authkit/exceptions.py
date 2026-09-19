"""Typed exception hierarchy for authkit.
 
All public exceptions inherit from AuthError.
Raise these from flow/service code — the router layer converts them
to FastAPI HTTPException. Never raise raw HTTPException outside routers.
"""
from __future__ import annotations

import re


class AuthError(Exception):
  """Base class for all authkit errors."""
  status_code: int = 400
  detail: str     = "Authentication error"
  code: str = "UNKNOWN_ERROR"

  def __init__(self, detail: str | None = None) -> None:
    self.detail = detail or self.__class__.detail
    super().__init__(self.detail)

  def __init_subclass__(cls, **kwargs: object) -> None:
    super().__init_subclass__(**kwargs)
    if "code" not in cls.__dict__:
      code = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
        "_",
        cls.__name__,
      ).upper()
      # ``OAuth`` is a word-like initialism (unlike all-caps ``MFA``), so a
      # generic CamelCase splitter sees it as ``O_Auth``. Keep public error
      # codes conventional and stable.
      cls.code = f"OAUTH{code[6:]}" if code.startswith("O_AUTH") else code

# ---- Registration -------------------------------------------
class EmailAlreadyExists(AuthError):
  """Raised when trying to register with an email that already exists."""

  status_code = 409
  detail = "An email address is already registered."

class UsernameAlreadyExists(AuthError):
  """Raised when trying to register with a username that already exists."""

  status_code = 409
  detail = "A user with that username already exists."

class PhoneAlreadyExists(AuthError):
  """Raised when trying to register with a phone number that already exists."""

  status_code = 409
  detail = "A user with that phone number already exists."


class RegistrationDisabled(AuthError):
  status_code = 403
  detail = "Registration is disabled."


class WeakPassword(AuthError):
  """Raised when password does not staisfy the configured password policy."""

  status_code = 422
  detail = "Password does not meet the required policy"


class InvalidEmail(AuthError):
  """Raised when an email address fails format validation."""

  status_code = 422
  detail = "Invalid email address"

# ---- Email verification --------------------------------------

class AlreadyVerified(AuthError):
  """Raised when attemmpting to verfy an already-verified email."""

  status_code = 409
  detail = "Email address is already verified."


class RateLimited(AuthError):
  """ Raised when a rate-limited action is attempted too soon."""

  status_code = 429
  detail = "Too many requests - please wait before trying again."

# ---- Login ------------------------------------------------

class InvalidCredentials(AuthError):
  """Raised on wrong eamil or password (intentionally generic message)."""

  status_code = 401
  detail = "Invalid credentials."
  code = "INVALID_CREDENTIALS"

class AccountLocked(AuthError):
  """Raised when too many failed login attempts trigger the account lockout policy."""

  status_code = 403
  detail = "Account is temporarily locked due to too many failed login attempts. Please try again later."


class EmailNotVerified(AuthError):
  """Raised when trying to log in with an unverified email address."""

  status_code = 403
  detail = "Email address is not verified."
  code = "EMAIL_NOT_VERIFIED"


class AccountInactive(AuthError):
  """Raised when trying to log in to an inactive account."""

  status_code = 403
  detail = "This account has been deactivated"
  code = "ACCOUNT_DISABLED"


class InvalidMFACode(AuthError):
  """Raised when TOTP or backup code is incorect."""

  status_code = 401
  detail = "Invalid MFA code."
  code = "INVALID_MFA_CODE"


class MFARequired(AuthError):
  """Raised when MFA is enabled but no MFA code is provided on login."""

  status_code = 403
  detail = "MFA code is required."
  code = "MFA_REQUIRED"


# ── Tokens ────────────────────────────────────────────────────────────────────
 
class InvalidToken(AuthError):
    """Raised when a token is malformed or has an invalid signature."""
 
    status_code = 400
    detail = "Invalid or malformed token"
 
 
class TokenExpired(AuthError):
    """Raised when a token's TTL has elapsed."""
 
    status_code = 400
    detail = "Token has expired"
    code = "TOKEN_EXPIRED"
 
 
class TokenRevoked(AuthError):
    """Raised when a token's jti is found in the blacklist."""
 
    status_code = 401
    detail = "Token has been revoked"
 
 
class TokenAlreadyUsed(AuthError):
    """Raised when a single-use token (e.g. password reset) is reused."""
 
    status_code = 400
    detail = "Token has already been used"
    code = "INVALID_RESET_TOKEN"
 
 
# ── Password flows ────────────────────────────────────────────────────────────
 
class SamePassword(AuthError):
    """Raised when new password is identical to the current password."""
 
    status_code = 422
    detail = "New password must differ from the current password"
 
 
class PasswordNotSet(AuthError):
    """Raised when an operation requires a password but none is set (OAuth-only account)."""
 
    status_code = 400
    detail = "No password is set on this account"
 
 
class PasswordAlreadySet(AuthError):
    """Raised when set-password is called on an account that already has a password."""
 
    status_code = 400
    detail = "A password is already set on this account"
 
 
# ── Users ─────────────────────────────────────────────────────────────────────
 
class UserNotFound(AuthError):
    """Raised when a user lookup fails and it is safe to surface that information."""
 
    status_code = 404
    detail = "User not found"
 
 
class ForbiddenError(AuthError):
    """Raised when a user lacks the required role or scope."""
 
    status_code = 403
    detail = "You do not have permission to perform this action"
    code = "PERMISSION_DENIED"


# ── MFA ───────────────────────────────────────────────────────────
class MFANotEnabled(AuthError):
    status_code = 400
    detail = "MFA is not enabled on this account"
class MFAAlreadyEnabled(AuthError):
    status_code = 409
    detail = "MFA is already enabled on this account"
class InvalidBackupCode(AuthError):
    status_code = 401
    detail = "Invalid or already used backup code"
 
 
# ── OAuth ─────────────────────────────────────────────────────────────────────
 
class OAuthProviderNotConfigured(AuthError):
    """Raised when a request targets an unconfigured or disabled OAuth provider."""
 
    status_code = 404
    detail = "OAuth provider is not configured or is disabled"
 
 
class OAuthStateMismatch(AuthError):
    """Raised when the OAuth state parameter does not match (CSRF protection)."""
 
    status_code = 400
    detail = "OAuth state mismatch — possible CSRF attack detected"
 
 
class OAuthCodeExchangeFailed(AuthError):
    """Raised when the authorization code → access token exchange fails."""
 
    status_code = 502
    detail = "Failed to exchange OAuth authorization code with provider"
 
 
class OAuthUserInfoFailed(AuthError):
    """Raised when fetching user info from the provider fails."""
 
    status_code = 502
    detail = "Failed to retrieve user information from OAuth provider"
 
 
class EmailAlreadyRegistered(AuthError):
    """Raised on OAuth callback when email matches a local account and auto-link is disabled."""
 
    status_code = 409
    detail = (
        "An account with this email already exists. "
        "Log in with your password to link accounts."
    )
 
 
class ProviderAlreadyLinked(AuthError):
    """Raised when a provider is already linked to the current account."""
 
    status_code = 409
    detail = "This OAuth provider is already linked to your account"
 
 
class LastLoginMethod(AuthError):
    """Raised when the user tries to remove their only remaining login method."""
 
    status_code = 400
    detail = "Cannot remove the last login method — add another before disconnecting"

class OAuthAccountNotFound(AuthError):
    status_code = 404
    detail = "No linked account found for this provider"
