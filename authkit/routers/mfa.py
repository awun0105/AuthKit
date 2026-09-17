"""MFA router authkit - etup, confirm, disable."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from authkit.audit import AuditEvent, AuditSink
from authkit.authentication.password import PasswordHandler
from authkit.core.config import AuthKitConfig
from authkit.events import AuthEvent, EventSink
from authkit.mfa.totp import MFASetupResult, confirm_mfa_flow, disable_mfa_flow, setup_mfa_flow
from authkit.models.requests import MessageResponse, MfaConfirmRequest, MfaDisableRequest
from authkit.models.user import UserInDB
from authkit.notifications.service import AbstractNotificationService
from authkit.routers._errors import handle_auth_errors
from authkit.storage.base import AbstractUserStore


def build_mfa_router(
    *,
    store: AbstractUserStore,
    config: AuthKitConfig,
    password_handler: PasswordHandler,
    notification_service: AbstractNotificationService,
    get_current_user: Callable,
    audit: AuditSink,
    events: EventSink,
) -> APIRouter:
  """Build the MFA APIRouter for one AuthKit instance.

  Returns:
      APIRouter with /mfa/setup, /mfa/confirm, /mfa/disable mounted.
  """
  router = APIRouter(prefix="/mfa")

  @router.post("/setup", response_model=MFASetupResult)
  @handle_auth_errors
  async def setup(user: UserInDB = Depends(get_current_user)) -> MFASetupResult:
    """Generate a TOTP and backup codes. Not active until confirm."""
    return await setup_mfa_flow(
      user.id, store=store, config=config, password_handler=password_handler
    )
  
  @router.post("/confirm", response_model=MessageResponse)
  @handle_auth_errors
  async def confirm(
    data: MfaConfirmRequest, user: UserInDB = Depends(get_current_user),
  ) -> MessageResponse:
    """Confirm MFA setup with the first TOTP code, activating MFA."""
    await confirm_mfa_flow(
      user.id, data.totp_code, store=store, notification_service=notification_service,
    )
    await audit.write(AuditEvent(action="mfa.enabled", user_id=user.id))
    await events.publish(AuthEvent(name="MFAEnabled", user_id=user.id))
    return MessageResponse(detail="MFA enabled sucessfully.")
  
  @router.post("/disable", response_model=MessageResponse)
  @handle_auth_errors
  async def disable(
    data: MfaDisableRequest, user: UserInDB = Depends(get_current_user),
  ):
    """Disable MFA - require password + TOTP or backup code."""
    await disable_mfa_flow(
      user.id, data.password, data.totp_or_backup_code,
      store=store, password_handler=password_handler,
      notification_service=notification_service
    )
    await audit.write(AuditEvent(action="mfa.disabled", user_id=user.id))
    await events.publish(AuthEvent(name="MFADisabled", user_id=user.id))
    return MessageResponse(detail="MFA disable successfully.")
  
  return router
