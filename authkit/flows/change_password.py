"""Change password flow (authenticated)."""
from __future__ import annotations

from authkit.authentication.jwt import JWTHandler
from authkit.authentication.password import PasswordHandler
from authkit.core.config import AuthKitConfig
from authkit.exceptions import InvalidCredentials, PasswordNotSet, SamePassword, UserNotFound
from authkit.models.token import TokenPair
from authkit.notifications.service import AbstractNotificationService
from authkit.session.base import AbstractSessionBackend
from authkit.session.refresh import RefreshTokenStore, record_from_token
from authkit.storage.base import AbstractUserStore
from authkit.utils import utcnow


async def change_password_flow(
    user_id: str,
    current_password: str,
    new_password: str,
    *,
    store: AbstractUserStore,
    config: AuthKitConfig,
    password_handler: PasswordHandler,
    jwt_handler: JWTHandler,
    notification_service: AbstractNotificationService,
    session_backend: AbstractSessionBackend | None = None,
    refresh_token_store: RefreshTokenStore | None = None,
) -> TokenPair:
    """Change the authenticated user's password.

    Returns a fresh TokenPair so the current session stays valid.

    Raises:
        UserNotFound, PasswordNotSet, InvalidCredentials, WeakPassword, SamePassword.
    """
    user = await store.get_by_id(user_id)
    if user is None:
        raise UserNotFound()
    if not user.hashed_password:
        raise PasswordNotSet()
    if not password_handler.verify_password(current_password, user.hashed_password):
        raise InvalidCredentials()

    password_handler.check_policy(new_password)

    if password_handler.verify_password(new_password, user.hashed_password):
        raise SamePassword()

    user.hashed_password = password_handler.hash_password(new_password)
    user.updated_at = utcnow()
    await store.update(user)
    if session_backend is not None:
        await session_backend.delete_all_for_user(user.id)
    if refresh_token_store is not None:
        await refresh_token_store.revoke_all_for_user(user.id)
    await notification_service.send_password_changed(user)
    pair = jwt_handler.create_token_pair(user.id, roles=user.roles, scopes=user.scopes)
    if refresh_token_store is not None:
        await refresh_token_store.register(record_from_token(jwt_handler, pair.refresh_token))
    return pair
