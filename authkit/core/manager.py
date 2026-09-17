"""AuthKit — the top-level facade for authkit.

Wires together password hashing, JWT, sessions, email/SMS notifications,
OAuth providers, and all flows behind a single object. Mount auth.router
on a FastAPI app and use auth.current_user / auth.require_role /
auth.require_permission as Depends() factories for your own routes.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from authkit.audit import AuditSink, NullAuditSink
from authkit.authentication.jwt import AbstractTokenBlacklist, JWTHandler, MemoryTokenBlacklist
from authkit.authentication.oauth import OAuthProviderBase, build_oauth_provider
from authkit.authentication.oauth_state import AbstractOAuthStateStore, MemoryOAuthStateStore
from authkit.authentication.password import PasswordHandler
from authkit.authorization.protocols import RBACStore
from authkit.core.backend import AuthBackend
from authkit.core.config import AuthKitConfig
from authkit.dependencies.current_user import build_get_current_user
from authkit.dependencies.permissions import build_require_roles, build_require_scopes
from authkit.email.base import AbstractEmailBackend
from authkit.email.console import ConsoleEmailBackend
from authkit.email.smtp import SmtpEmailBackend
from authkit.email.templates import EmailTemplates
from authkit.events import EventSink, InProcessEventBus
from authkit.gateway import AuthGateway
from authkit.notifications.service import AbstractNotificationService, NotificationService
from authkit.routers.admin import build_admin_router
from authkit.routers.auth import build_auth_router
from authkit.routers.mfa import build_mfa_router
from authkit.routers.oauth import build_oauth_router
from authkit.session.base import AbstractSessionBackend
from authkit.session.memory import MemorySessionBackend
from authkit.sms.base import AbstractSmsBackend
from authkit.sms.templates import SmsTemplates
from authkit.storage.base import AbstractUserStore


def _build_email_backend(config: AuthKitConfig) ->AbstractEmailBackend:
  """Build the default email backend from config.

  Only "console" and "smtp" are auto-selectable from config — SendGrid
  and Mailgun have no static credentials format that fits a single
  config field cleanly, so pass them explicitly via the email_backend
  constructor argument instead.
  """
  if config.email_backend == "smtp":
    return SmtpEmailBackend.from_config(config)
  return ConsoleEmailBackend()


def _build_session_backend(config: AuthKitConfig) -> AbstractSessionBackend | None:
  """Build a default session backend from config, or None if disabled"""
  if config.session_backend == "memory":
    return MemorySessionBackend()
  if config.session_backend == "redis":
    if not config.redis_url:
      raise ValueError("session_backend='redis' requires redis_url to be set")
    from authkit.session.redis import RedisSessionBackend
    return RedisSessionBackend(config.redis_url)
  return None


def _build_oauth_providers(config: AuthKitConfig) -> dict[str, OAuthProviderBase]:
  """Build all configured and enabled OAuth providers from config."""
  providers: dict[str, OAuthProviderBase] = {}
  for name, provider_config in config.oauth_providers.items():
    if not provider_config.enabled:
      continue
    providers[name] = build_oauth_provider(
      name, provider_config,
      apple_team_id=config.apple_team_id,
      apple_key_id=config.apple_key_id,
      apple_private_key_pem=config.apple_private_key_pem,
    )
  return providers


class AuthKit:
  """Top-level facade for authkit.

  Usage::

      auth = AuthKit(
          config=AuthKitConfig(secret_key="replace-with-at-least-32-random-bytes"),
          user_store=MyUserStore(),
      )
      app.include_router(auth.router, prefix="/auth", tags=["auth"])

      @app.get("/profile")
      async def profile(user=Depends(auth.current_user)):
          return user

      @app.delete("/admin/users")
      async def delete_user(user=Depends(auth.require_roles("admin"))):
          ...
  """

  def __init__(
    self,
    config: AuthKitConfig,
    backend: AuthBackend | None = None,
    *,
    user_store: AbstractUserStore | None = None,
    email_backend: AbstractEmailBackend | None = None,
    sms_backend: AbstractSmsBackend | None = None,
    notification_service: AbstractNotificationService | None = None,
    email_templates: EmailTemplates | None = None,
    sms_templates: SmsTemplates | None = None,
    password_handler: PasswordHandler | None = None,
    token_blacklist: AbstractTokenBlacklist | None = None,
    session_backend: AbstractSessionBackend | None = None,
    oauth_state_store: AbstractOAuthStateStore | None = None,
    rbac_store: RBACStore | None = None,
    audit_sink: AuditSink | None = None,
    event_sink: EventSink | None = None,
  ) -> None:
    """Construct an AuthKit instance.

    Args:
        config:     Application AuthKitConfig.
        user_store: Consumer's AbstractUserStore implementation.
        email_backend, sms_backend: Override the auto-selected backends.
            Required for SendGrid, Mailgun, Twilio, or AWS SNS — these
            have no config-driven auto-selection, pass an instance directly.
        notification_service: Fully override notification routing.
        email_templates, sms_templates: Override default copy.
        password_handler: Override the default PasswordHandler.
        token_blacklist:  Override the default MemoryTokenBlacklist
            (pass a RedisTokenBlacklist for multi-process deployments).
        session_backend:  Override the config-driven session backend.
        oauth_state_store: Override the default MemoryOAuthStateStore
            (use a Redis-backed implementation for multi-process deployments).
    """
    if backend is None and user_store is None:
      raise TypeError("AuthKit requires either backend= or user_store=")
    if backend is not None and user_store is not None:
      raise TypeError("Pass backend= or user_store=, not both")

    self.config = config
    self.backend = backend
    resolved_store = backend.users if backend is not None else user_store
    assert resolved_store is not None
    self.store: AbstractUserStore = resolved_store
    self.rbac = rbac_store if rbac_store is not None else (backend.rbac if backend else None)
    self.refresh_tokens = backend.refresh_tokens if backend else None
    self.audit = audit_sink or (backend.audit if backend and backend.audit else NullAuditSink())
    self.events = event_sink or InProcessEventBus()
    self.gateway = AuthGateway(self.store)

    self.password_handler = password_handler or PasswordHandler(config)
    resolved_blacklist = token_blacklist
    if resolved_blacklist is None and backend is not None:
      resolved_blacklist = backend.token_blacklist
    self.jwt_handler = JWTHandler(config, blacklist=resolved_blacklist or MemoryTokenBlacklist())
    self.session_backend: AbstractSessionBackend | None
    if session_backend is not None:
      self.session_backend = session_backend
    elif backend is not None:
      self.session_backend = backend.sessions
    else:
      self.session_backend = _build_session_backend(config)

    resolved_email_backend = email_backend or _build_email_backend(config)
    self.notification_service = notification_service or NotificationService(
      config=config,
      email_backend=resolved_email_backend,
      sms_backend=sms_backend,
      email_templates=email_templates,
      sms_templates=sms_templates,
    )

    backend_oauth_states = backend.oauth_states if backend is not None else None
    self.oauth_state_store = oauth_state_store or backend_oauth_states or MemoryOAuthStateStore()
    self.oauth_providers = _build_oauth_providers(config)

    # Dependecy factories - built once, reused accross all routes
    self._get_current_user = build_get_current_user(self.jwt_handler, self.store)
    self._require_roles_factory = build_require_roles(self.jwt_handler)
    self._require_scopes_factory = build_require_scopes(self.jwt_handler)

    self._router = self._build_router()

  def _build_router(self) -> APIRouter:
    """Assemble the combined router from auth, mfa, and oauth sub-routers."""
    router = APIRouter()
    router.include_router(build_auth_router(
        store=self.store, config=self.config, password_handler=self.password_handler,
        jwt_handler=self.jwt_handler, notification_service=self.notification_service,
        session_backend=self.session_backend, get_current_user=self._get_current_user,
        refresh_token_store=self.refresh_tokens, audit=self.audit, events=self.events,
    ))
    router.include_router(build_mfa_router(
        store=self.store, config=self.config, password_handler=self.password_handler,
        notification_service=self.notification_service, get_current_user=self._get_current_user,
        audit=self.audit, events=self.events,
    ))
    router.include_router(build_oauth_router(
        store=self.store, config=self.config, jwt_handler=self.jwt_handler,
        notification_service=self.notification_service, providers=self.oauth_providers,
        state_store=self.oauth_state_store, get_current_user=self._get_current_user,
        refresh_token_store=self.refresh_tokens,
        audit=self.audit, events=self.events,
    ))
    if self.config.enable_admin_router:
      if self.rbac is None:
        raise ValueError("enable_admin_router=True requires a backend with an RBAC store")
      router.include_router(build_admin_router(
        rbac=self.rbac,
        get_current_user=self._get_current_user,
        audit=self.audit,
        events=self.events,
      ))
    return router

  @property
  def router(self) -> APIRouter:
    """The combined FastAPI router — mount with app.include_router(auth.router, prefix='/auth')."""
    return self._router
  
  @property
  def current_user(self) -> Callable:
    """Depends()-compatible callable resolving the authenticated user.

    Usage: ``user=Depends(auth.current_user)``
    """
    return self._get_current_user
  
  def require_roles(self, *roles: str, require_all: bool = False) -> Callable:
      """Build a Depends()-compatible role-check dependency.

      Args:
          roles:       Role(s) to require.
          require_all: If True, all roles required; if False, any one suffices.

      Usage: ``Depends(auth.require_roles("admin"))``
      """
      return self._require_roles_factory(*roles, require_all=require_all)

  def require_role(self, role: str) -> Callable:
      """Require one consumer-defined role."""
      return self.require_roles(role)

  def require_scopes(self, *scopes: str, require_all: bool = False) -> Callable:
      """Build a Depends()-compatible scope-check dependency.

      Args:
          scopes:      Scope(s) to require.
          require_all: If True, all scopes required; if False, any one suffices.

      Usage: ``Depends(auth.require_scopes("write"))``
      """
      return self._require_scopes_factory(*scopes, require_all=require_all)

  def require_permission(self, permission: str) -> Callable:
      """Require one permission.

      Permissions use the existing JWT ``scopes`` claim so AuthKit has one
      permission mechanism rather than competing scope/permission systems.
      """
      return self.require_scopes(permission)
