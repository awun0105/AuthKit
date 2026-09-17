"""OTP-based password reset flow."""
from __future__ import annotations

from authkit.authentication.password import PasswordHandler
from authkit.core.config import AuthKitConfig
from authkit.exceptions import InvalidToken, SamePassword, TokenExpired
from authkit.notifications.service import AbstractNotificationService
from authkit.session.base import AbstractSessionBackend
from authkit.session.refresh import RefreshTokenStore
from authkit.storage.base import AbstractUserStore
from authkit.utils import utcnow, verify_token_hash


async def reset_password_otp_flow(
    identifier: str,
    otp: str,
    new_password: str,
    *,
    store: AbstractUserStore,
    config: AuthKitConfig,
    password_handler: PasswordHandler,
    notification_service: AbstractNotificationService,
    session_backend: AbstractSessionBackend | None = None,
    refresh_token_store: RefreshTokenStore | None = None,
) -> None:
    """Reset password using an OTP received via email or SMS.

    Args:
        identifier:  Email address or phone number used when requesting reset.
        otp:         The OTP the user received.
        new_password: The desired new password.

    Raises:
        TokenExpired: OTP has expired.
        InvalidToken: OTP incorrect or user not found.
        WeakPassword: New password violates policy.
        SamePassword: New password matches current password.
    """
    user = await store.get_by_email(identifier)
    if user is None:
        user = await store.get_by_phone(identifier)
    if user is None:
        raise InvalidToken()

    if not user.reset_otp_expires_at or utcnow() > user.reset_otp_expires_at:
        raise TokenExpired()

    # Attempt limit
    if config.max_otp_attempts > 0 and user.reset_otp_attempts >= config.max_otp_attempts:
        user.reset_otp_hash = None
        user.reset_otp_expires_at = None
        user.reset_otp_attempts = 0
        user.updated_at = utcnow()
        await store.update(user)
        raise TokenExpired("Too many attempts — please request a new reset code.")

        

    if not user.reset_otp_hash or not verify_token_hash(otp, user.reset_otp_hash):
        if config.max_otp_attempts > 0:
            user.reset_otp_attempts += 1
            user.updated_at = utcnow()
            await store.update(user)
        raise InvalidToken()

    password_handler.check_policy(new_password)

    if user.hashed_password and password_handler.verify_password(new_password, user.hashed_password):
        raise SamePassword()

    user.hashed_password = password_handler.hash_password(new_password)
    user.reset_otp_hash = None
    user.reset_otp_expires_at = None
    user.reset_otp_attempts = 0
    user.updated_at = utcnow()
    await store.update(user)
    if session_backend is not None:
        await session_backend.delete_all_for_user(user.id)
    if refresh_token_store is not None:
        await refresh_token_store.revoke_all_for_user(user.id)
    await notification_service.send_password_changed(user)
