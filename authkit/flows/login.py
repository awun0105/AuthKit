"""Login flow - suports email, username, and phone identifiers"""
from __future__ import annotations

from datetime import timedelta

import pyotp

from authkit.authentication.jwt import JWTHandler
from authkit.authentication.password import PasswordHandler
from authkit.core.config import AuthKitConfig
from authkit.exceptions import (
  AccountInactive,
  AccountLocked,
  EmailNotVerified,
  InvalidCredentials,
  InvalidMFACode,
  MFARequired,
)
from authkit.mfa.backup_codes import consume_backup_code
from authkit.models.token import TokenPair
from authkit.models.user import UserInDB, UserRead
from authkit.session.base import AbstractSessionBackend, SessionData
from authkit.session.refresh import RefreshTokenStore, record_from_token
from authkit.storage.base import AbstractUserStore
from authkit.utils import utcnow

_DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$dummydummydummy$dummydummydummydummydummydummy"
 

async def _resolve_user(
  identifier: str,
  store: AbstractUserStore,
  config: AuthKitConfig
) -> UserInDB | None:
  """Try each configured identifier field in order, return first match."""
  for field in config.login_identifier_fields:
    user: UserInDB | None = None
    if field == "email":
      user = await store.get_by_email(identifier)
    elif field == "username":
      user = await store.get_by_username(identifier)
    elif field == "phone":
      user = await store.get_by_phone(identifier)
    if user is  not None:
      return user
  return None

async def login_flow(
    identifier: str,
    password: str,
    *,
    store: AbstractUserStore,
    config: AuthKitConfig,
    password_handler: PasswordHandler,
    jwt_handler: JWTHandler,
    totp_code: str | None = None,
    session_backend: AbstractSessionBackend | None = None,
    user_agent: str | None = None,
    ip_hash: str | None = None,
    refresh_token_store: RefreshTokenStore | None = None,
) -> tuple[TokenPair, UserRead]:
    """Authenticate a user and issue a token pair.
 
    The ``identifier`` is matched against ``config.login_identifier_fields``
    in order — e.g. ``["email", "username", "phone"]`` tries email first,
    then username, then phone.
 
    Args:
        identifier:   Email, username, or phone number.
        password:     Plain-text password.
        store:        User store.
        config:       Application config.
        password_handler: Password handler.
        jwt_handler:  JWT handler.
        totp_code:    TOTP code — required when MFA is enabled.
        session_backend: Optional session backend.
        user_agent:   HTTP User-Agent for session fingerprinting.
        ip_hash:      Hashed client IP for session fingerprinting.
 
    Returns:
        Tuple of (TokenPair, UserRead).
 
    Raises:
        InvalidCredentials: Identifier not found or password wrong.
        AccountInactive:    Account deactivated.
        EmailNotVerified:   Email not verified (when required).
        MFARequired:        MFA enabled but no totp_code supplied.
        InvalidMFACode:     Wrong TOTP code.
    """
    user = await _resolve_user(identifier, store, config)

    # Always run a dummy verify to normalize timing
    if user is None or not user.hashed_password:
      password_handler.verify_password(password, _DUMMY_HASH)
      raise InvalidCredentials()

    # Check lockout BEFORE password verification
    if user.locked_until and utcnow() < user.locked_until:
        raise AccountLocked()
    
    ok, new_hash = password_handler.verify_and_update(password, user.hashed_password)
    if not ok:
      if config.max_failed_attempts > 0:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= config.max_failed_attempts:
          user.locked_until = utcnow() + timedelta(seconds=config.login_lockout_duration)
        user.updated_at = utcnow()
        await store.update(user)
      raise InvalidCredentials()
    
    if not user.is_active:
      raise AccountInactive()
    
    if config.require_email_verification and not user.is_verified:
      raise EmailNotVerified()
    
    if config.enable_mfa and user.mfa_enabled:
      if not user.mfa_secret:
        raise InvalidMFACode()
      if not totp_code:
        raise MFARequired()
      totp_valid = pyotp.TOTP(user.mfa_secret).verify(totp_code, valid_window=1)
      if not totp_valid:
        consumed = await consume_backup_code(user, totp_code, password_handler, store)
        if not consumed:
          raise InvalidMFACode()

    # Success- reset brute-force counters + silent rehash
    user.failed_login_attempts = 0
    user.locked_until = None
    if new_hash:
      user.hashed_password = new_hash
    user.updated_at = utcnow()
    await store.update(user)


    session_id: str | None = None
    if session_backend is not None:
      session = await session_backend.create(SessionData(
        user_id=user.id,
        user_agent=user_agent,
        ip_hash=ip_hash,
        expires_at=utcnow() + timedelta(seconds=config.refresh_token_ttl),
      ))
      session_id = session.session_id

    pair = jwt_handler.create_token_pair(
      user.id,
      roles=user.roles,
      scopes=user.scopes,
      session_id=session_id,
    )
    if refresh_token_store is not None:
      await refresh_token_store.register(record_from_token(jwt_handler, pair.refresh_token))

    return pair, user.to_read()
