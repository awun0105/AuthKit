"""Explicit central configuration for AuthKit.

The constructor never reads process-global environment or a ``.env`` file.
Use :meth:`AuthKitConfig.from_env` when environment loading is desired.

Example::

  # Direct
  config = AuthKitConfig(secret_key="a-random-secret-of-at-least-32-bytes")

  # Explicit environment helper
  # AUTHKIT_SECRET_KEY=... python app.py
  config = AuthKitConfig.from_env()
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _default_login_fields() -> list[Literal["email", "username", "phone"]]:
  return ["email"]


def _default_channels() -> list[Literal["email", "sms"]]:
  return ["email"]


class OAuthProviderConfig(BaseModel):
  """Configuration for a single OAuth 2.0 / OIDC provider.

  Attributes:
      client_id:     OAuth application client ID.
      client_secret: OAuth application client secret.
                      For Apple, leave empty — the secret is generated
                      dynamically from apple_private_key_pem.
      redirect_uri:  Callback URL. Must match exactly what is registered
                      in the provider's developer console.
      scopes:        Override the provider's default scopes. Empty list
                      means use built-in provider defaults.
      enabled:       Set False to temporarily disable without removing config.
  """

  client_id: str
  client_secret: str
  redirect_uri: str
  scopes: list[str] = Field(default_factory=list)
  enabled: bool = True


class AuthKitConfig(BaseModel):
  """Top-level configuration object for AuthKit.

  Values are constructor-only by default. ``from_env`` is an explicit
  convenience for CLI/deployment use and reads only ``AUTHKIT_*`` variables.
  """

  model_config = ConfigDict(extra="forbid")

  # ── JWT ───────────────────────────────────────────────────────────────────
  secret_key: str
  algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
  access_token_ttl: int = Field(default=900, gt=0)          # seconds — 15 minutes
  refresh_token_ttl: int = Field(default=604800, gt=0)      # seconds — 7 days
  enable_refresh_rotation: bool = True

  # ── Passwords ─────────────────────────────────────────────────────────────
  password_hasher: Literal["argon2", "bcrypt"] = "argon2"
  min_password_length: int = Field(default=8, ge=8)
  require_password_uppercase: bool = False
  require_password_digit: bool = False
  require_password_special: bool = False

  # ---- brute-force protection ------------------------------------------------------
  max_failed_attempts: int = 5  # 0 = disable
  login_lockout_duration: int = 900   # seconds — 15 minutes
  max_otp_attempts: int = 5       # 0 = disable

  # ── Email ─────────────────────────────────────────────────────────────────
  email_backend: Literal["smtp", "console"] = "console"
  smtp_host: str = "localhost"
  smtp_port: int = 587
  smtp_username: str | None = None
  smtp_password: str | None = None
  smtp_use_tls: bool = True
  emails_from_name: str = "AuthKit"
  emails_from_address: str = "noreply@example.com"

  # ---- SMS -----------------------------------------------------------------
  twilio_account_sid: str | None = None
  twilio_auth_token: str | None = None
  twilio_from_number: str | None = None
  aws_sns_region: str | None = None
  aws_sns_sender_id: str | None = None

  # ---- Login identifiers ---------------------------------------------------
  # Tried in order - first match wins
  # e.g ["email", "username", "phone"] tries email first, then username
  login_identifier_fields: list[Literal["email", "username", "phone"]] = Field(
      default_factory=_default_login_fields
  )

  # ---- Verification --------------------------------------------------------
  verification_method: Literal["link", "otp"] = "link"
  verification_channels: list[Literal["email", "sms"]] = Field(
      default_factory=_default_channels
  )
  otp_length: int = Field(default=6, ge=6, le=10)
  otp_ttl: int = Field(default=600, gt=0) # 10 minutes

  # ---- Password Request ----------------------------------------------------
  password_reset_method: Literal["link", "otp"] = "link"
  password_reset_channels: list[Literal["email", "sms"]] = Field(
      default_factory=_default_channels
  )

  # ── Token TTLs for flows ──────────────────────────────────────────────────
  email_verification_ttl: int = 86400     # 24 hours
  password_reset_ttl: int = 3600          # 1 hour
  resend_verification_cooldown: int = 60  # 1 minute rate limit

  # ── Registration ──────────────────────────────────────────────────────────
  require_email_verification: bool = True
  allow_registration: bool = True

  # ── Session ───────────────────────────────────────────────────────────────
  session_backend: Literal["memory", "redis"] | None = None
  redis_url: str | None = None

  # ── MFA ───────────────────────────────────────────────────────────────────
  enable_mfa: bool = False
  mfa_issuer_name: str = "AuthKit"

  # ── OAuth ─────────────────────────────────────────────────────────────────
  oauth_providers: dict[str, OAuthProviderConfig] = Field(default_factory=dict)
  auto_link_by_email: bool = True  # Case 2 account linking

  # Apple Sign In — required only when "apple" provider is configured
  apple_team_id: str | None = None
  apple_key_id: str | None = None
  apple_private_key_pem: str | None = None  # full contents of the .p8 file

  # ── Frontend URLs (used in email links) ───────────────────────────────────
  frontend_base_url: str = "http://localhost:3000"
  verify_email_path: str = "/auth/verify-email"
  reset_password_path: str = "/auth/reset-password"

  # ── Optional administration surface ──────────────────────────────────────
  enable_admin_router: bool = False

  # ── Browser refresh-cookie mode (off by default; Bearer body still works) ─
  enable_refresh_cookie: bool = False
  refresh_cookie_name: str = "authkit_refresh"
  refresh_cookie_secure: bool = True
  refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
  refresh_cookie_path: str = "/"
  refresh_cookie_domain: str | None = None
  authenticated_cookie_name: str = "authkit_authenticated"

  @field_validator("secret_key")
  @classmethod
  def validate_secret_key(cls, value: str) -> str:
      if len(value.encode("utf-8")) < 32:
          raise ValueError("secret_key must contain at least 32 bytes")
      return value

  @model_validator(mode="after")
  def validate_cookie_security(self) -> AuthKitConfig:
      if self.refresh_cookie_samesite == "none" and not self.refresh_cookie_secure:
          raise ValueError("SameSite=None refresh cookies must also set Secure")
      return self

  @classmethod
  def from_env(
      cls,
      *,
      env_file: str | Path | None = None,
      prefix: str = "AUTHKIT_",
      **overrides: Any,
  ) -> AuthKitConfig:
      """Load an explicit AuthKit-prefixed environment configuration.

      Structured values (lists/dicts) must use JSON. A supplied env file is
      parsed as simple ``KEY=value`` pairs and never loaded implicitly.
      Constructor ``overrides`` take precedence over file and environment.
      """

      values: dict[str, Any] = {}
      file_values: dict[str, str] = {}
      if env_file is not None:
          for raw_line in Path(env_file).read_text(encoding="utf-8").splitlines():
              line = raw_line.strip()
              if not line or line.startswith("#") or "=" not in line:
                  continue
              key, raw_value = line.split("=", 1)
              file_values[key.strip()] = raw_value.strip().strip('"').strip("'")

      for field_name in cls.model_fields:
          env_name = f"{prefix}{field_name.upper()}"
          raw = os.environ.get(env_name, file_values.get(env_name))
          if raw is None:
              continue
          if raw.startswith(("[", "{")):
              values[field_name] = json.loads(raw)
          else:
              values[field_name] = raw
      values.update(overrides)
      return cls.model_validate(values)
