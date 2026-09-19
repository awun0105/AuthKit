"""Core authentication router for authkit.
 
build_auth_router() is called once by AuthKit.__init__ with all the
instance-specific dependencies closed over, since each AuthKit instance
has its own store/config/handlers. Mounted by the AuthKit facade as
part of auth.router.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from authkit.audit import AuditEvent, AuditSink
from authkit.authentication.jwt import JWTHandler
from authkit.authentication.password import PasswordHandler
from authkit.core.config import AuthKitConfig
from authkit.events import AuthEvent, EventSink
from authkit.exceptions import AuthError
from authkit.flows.change_password import change_password_flow
from authkit.flows.forgot_password import forgot_password_flow
from authkit.flows.login import login_flow
from authkit.flows.logout import logout_flow
from authkit.flows.refresh import refresh_flow
from authkit.flows.register import register_flow
from authkit.flows.resend_verification import resend_verification_flow
from authkit.flows.reset_password import reset_password_flow
from authkit.flows.reset_password_otp import reset_password_otp_flow
from authkit.flows.set_password import set_password_flow
from authkit.flows.verify_email import verify_email_flow
from authkit.flows.verify_otp import verify_otp_flow
from authkit.models.requests import (
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  MessageResponse,
  PublicAuthConfig,
  ResendVerificationRequest,
  ResetPasswordOtpRequest,
  ResetPasswordRequest,
  SessionRead,
  SetPasswordRequest,
  TokenResponse,
  VerifyEmailRequest,
  VerifyOtpRequest,
)
from authkit.models.token import LogoutRequest, RefreshTokenRequest, TokenPair
from authkit.models.user import UserCreate, UserInDB, UserRead
from authkit.notifications.service import AbstractNotificationService
from authkit.routers._errors import handle_auth_errors
from authkit.routers.cookies import (
  clear_refresh_cookies,
  enforce_cookie_csrf,
  refresh_token_from_request,
  set_refresh_cookies,
)
from authkit.session.base import AbstractSessionBackend
from authkit.session.refresh import RefreshTokenStore
from authkit.storage.base import AbstractUserStore
from authkit.utils import hash_token

_bearer_scheme = HTTPBearer(auto_error=True)


def _request_fingerprint(request: Request) -> tuple[str | None, str | None]:
    """Return (user_agent, hashed client IP) for session/audit records."""
    user_agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        host = forwarded.split(",", 1)[0].strip()
    elif request.client is not None:
        host = request.client.host
    else:
        host = ""
    return user_agent, hash_token(host) if host else None


def build_auth_router(
  *,
  store: AbstractUserStore,
  config: AuthKitConfig,
  password_handler: PasswordHandler,
  jwt_handler: JWTHandler,
  notification_service: AbstractNotificationService,
  session_backend: AbstractSessionBackend | None,
  get_current_user: Callable,
  refresh_token_store: RefreshTokenStore | None,
  audit: AuditSink,
  events: EventSink,
) -> APIRouter:
  """Build the core auth APIRouter for one AuthKit instance.

  Args:
      store, config, password_handler, jwt_handler, notification_service:
          Instance-specific handlers built by AuthKit.
      session_backend: Optional — None disables session creation on login.
      get_current_user: The current_user dependency built for this instance.

  Returns:
      A fully wired APIRouter with all core auth endpoints.
  """
  router = APIRouter()

  @router.post("/register", response_model=UserRead, status_code=201)
  @handle_auth_errors
  async def register(data: UserCreate) -> UserRead:
    """Register a new user account"""
    user = await register_flow(
      data, store=store, config=config,
      password_handler=password_handler, notification_service=notification_service,
    )
    await audit.write(AuditEvent(action="user.registered", user_id=user.id))
    await events.publish(AuthEvent(name="UserRegistered", user_id=user.id))
    return user
  
  @router.post("/verify-email", response_model=UserRead)
  @handle_auth_errors
  async def verify_email(data: VerifyEmailRequest) -> UserRead:
    """Verify email using signed link token"""
    user = await verify_email_flow(
      data.token, store=store, config=config,
      notification_service=notification_service
    )
    await audit.write(AuditEvent(action="email.verified", user_id=user.id))
    await events.publish(AuthEvent(name="UserVerified", user_id=user.id))
    return user
  
  @router.post("/verify-otp", response_model=UserRead)
  @handle_auth_errors
  async def verify_otp(data: VerifyOtpRequest) -> UserRead:
    """Verify account using OTP"""
    user = await verify_otp_flow(
      data.identifier, data.otp,
      store=store, config=config, notification_service=notification_service
    )
    await audit.write(AuditEvent(action="email.verified", user_id=user.id))
    await events.publish(AuthEvent(name="UserVerified", user_id=user.id))
    return user
  
  @router.post("/resend-verification", response_model=MessageResponse)
  @handle_auth_errors
  async def resend_verification(data: ResendVerificationRequest) -> MessageResponse:
    """Resend the verification link or OTP. Always returns 200 (anti-enumeration)."""
    await resend_verification_flow(
      data.identifier, store=store, config=config, notification_service=notification_service,
    )
    return MessageResponse(detail="If this account exists, a verification message was sent.")
  
  @router.get("/config", response_model=PublicAuthConfig)
  async def public_config() -> PublicAuthConfig:
    """Non-secret settings the frontend uses to render the correct screens."""
    return PublicAuthConfig(
      allow_registration=config.allow_registration,
      require_email_verification=config.require_email_verification,
      verification_method=config.verification_method,
      password_reset_method=config.password_reset_method,
      enable_mfa=config.enable_mfa,
      oauth_providers=[
        name for name, provider in config.oauth_providers.items() if provider.enabled
      ],
      refresh_cookie=config.enable_refresh_cookie,
    )

  @router.get("/me", response_model=UserRead)
  @handle_auth_errors
  async def me(user: UserInDB = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user after reloading from storage."""
    return user.to_read()

  @router.get("/sessions", response_model=list[SessionRead])
  @handle_auth_errors
  async def list_sessions(user: UserInDB = Depends(get_current_user)) -> list[SessionRead]:
    """List active sessions when a session backend is configured."""
    if session_backend is None:
      return []
    sessions = await session_backend.get_all_for_user(user.id)
    return [
      SessionRead(
        session_id=item.session_id,
        user_agent=item.user_agent,
        issued_at=item.issued_at,
        expires_at=item.expires_at,
      )
      for item in sessions
    ]

  @router.post("/login", response_model=TokenResponse)
  @handle_auth_errors
  async def login(data: LoginRequest, request: Request, response: Response) -> TokenResponse:
    """Authenticate and return an access + refresh token pair."""
    user_agent, ip_hash = _request_fingerprint(request)
    try:
      pair, user = await login_flow(
        data.identifier, data.password,
        store=store, config=config, password_handler=password_handler,
        jwt_handler=jwt_handler, totp_code=data.totp_code,
        session_backend=session_backend,
        user_agent=user_agent,
        ip_hash=ip_hash,
        refresh_token_store=refresh_token_store,
      )
    except AuthError:
      await audit.write(AuditEvent(
          action="user.login_failed", ip_hash=ip_hash, user_agent=user_agent,
      ))
      raise
    await audit.write(AuditEvent(
        action="user.login_succeeded", user_id=user.id,
        ip_hash=ip_hash, user_agent=user_agent,
    ))
    set_refresh_cookies(response, pair.refresh_token, config)
    return TokenResponse(
      access_token=pair.access_token, refresh_token=pair.refresh_token,
      token_type=pair.token_type, user=user
    )
  
  @router.post("/logout", status_code=204)
  @handle_auth_errors
  async def logout(
    request: Request,
    response: Response,
    data: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)
  ) -> Response:
    """Revoke the current access token (and refresh token if provided)."""
    body_refresh = data.refresh_token if data else None
    cookie_refresh = (
      request.cookies.get(config.refresh_cookie_name)
      if config.enable_refresh_cookie else None
    )
    if cookie_refresh and not body_refresh:
      enforce_cookie_csrf(request)
    refresh_token = body_refresh or cookie_refresh
    payload = jwt_handler.decode_token(credentials.credentials, expected_type="access")
    await logout_flow(
      credentials.credentials,
      jwt_handler=jwt_handler,
      refresh_token=refresh_token,
      session_backend=session_backend,
      session_id=payload.sid,
      refresh_token_store=refresh_token_store,
    )
    await audit.write(AuditEvent(action="user.logout", user_id=payload.sub))
    clear_refresh_cookies(response, config)
    # Preserve the response headers carrying the refresh-cookie deletions.
    response.status_code = 204
    return response

  @router.post("/refresh", response_model=TokenPair)
  @handle_auth_errors
  async def refresh(
    request: Request,
    response: Response,
    data: RefreshTokenRequest | None = None,
  ) -> TokenPair:
    """Exchange a valid refresh token for a new token pair."""
    token = refresh_token_from_request(
      request, data.refresh_token if data else None, config,
    )
    pair = await refresh_flow(
      token,
      store=store,
      config=config,
      jwt_handler=jwt_handler,
      refresh_token_store=refresh_token_store,
    )
    payload = jwt_handler.decode_token(pair.access_token)
    await audit.write(AuditEvent(action="session.refreshed", user_id=payload.sub))
    set_refresh_cookies(response, pair.refresh_token, config)
    return pair
  
  @router.post("/forgot-password", response_model=MessageResponse)
  @handle_auth_errors
  async def forgot_password(data: ForgotPasswordRequest) -> MessageResponse:
    """Request a password rest lonk or OTP. Always returns 200 (anti-enumeration)."""
    await forgot_password_flow(
      data.identifier, store=store, config=config, notification_service=notification_service
    )
    return MessageResponse(detail="If this account exists, a reset message was sent.")
  
  @router.post("/reset-password", response_model=MessageResponse)
  @handle_auth_errors
  async def reset_password(data: ResetPasswordRequest) -> MessageResponse:
    """Reset password using a signed link token"""
    await reset_password_flow(
      data.token, data.new_password, store=store, config=config,
      password_handler=password_handler, notification_service=notification_service,
      session_backend=session_backend, refresh_token_store=refresh_token_store,
    )
    await audit.write(AuditEvent(action="password.reset_completed"))
    return MessageResponse(detail="Password reset successfully.")

  @router.post("/reset-password-otp", response_model=MessageResponse)
  @handle_auth_errors
  async def reset_password_otp(data: ResetPasswordOtpRequest) -> MessageResponse:
    """Reset password using OTP code"""
    await reset_password_otp_flow(
      data.identifier, data.otp, data.new_password, store=store, config=config,
      password_handler=password_handler, notification_service=notification_service,
      session_backend=session_backend, refresh_token_store=refresh_token_store,
    )
    await audit.write(AuditEvent(action="password.reset_completed"))
    return MessageResponse(detail="Password reset successfully.")
  
  @router.post("/change-password", response_model=TokenPair)
  @handle_auth_errors
  async def change_password(
    data: ChangePasswordRequest,
    response: Response,
    user: UserInDB = Depends(get_current_user),
  ) -> TokenPair:
    """Change password for the authenticated user. Returns a fresh token pair."""
    pair = await change_password_flow(
      user.id, data.current_password, data.new_password,
      store=store, config=config, password_handler=password_handler,
      jwt_handler=jwt_handler, notification_service=notification_service,
      session_backend=session_backend, refresh_token_store=refresh_token_store,
    )
    await audit.write(AuditEvent(action="password.changed", user_id=user.id))
    await events.publish(AuthEvent(name="PasswordChanged", user_id=user.id))
    set_refresh_cookies(response, pair.refresh_token, config)
    return pair
  
  @router.post("/set-password", response_model=MessageResponse)
  @handle_auth_errors
  async def set_password(
    data: SetPasswordRequest,
    user: UserInDB = Depends(get_current_user),
  ) -> MessageResponse:
    """Add a password login method to an OAuth-only account."""
    await set_password_flow(
      user.id, data.new_password, store=store, config=config,
      password_handler=password_handler, notification_service=notification_service
    )
    await audit.write(AuditEvent(action="password.changed", user_id=user.id))
    await events.publish(AuthEvent(name="PasswordChanged", user_id=user.id))
    
    return MessageResponse(detail="Password set successfully.")

  return router
  
