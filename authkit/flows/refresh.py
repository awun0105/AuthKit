"""Token refresh flow."""
from __future__ import annotations

import time

from authkit.authentication.jwt import JWTHandler
from authkit.core.config import AuthKitConfig
from authkit.exceptions import InvalidToken, TokenRevoked
from authkit.models.token import TokenPair
from authkit.session.refresh import RefreshTokenStore, record_from_token
from authkit.storage.base import AbstractUserStore


async def refresh_flow(
    refresh_token: str,
    *,
    store: AbstractUserStore,
    config: AuthKitConfig,
    jwt_handler: JWTHandler,
    refresh_token_store: RefreshTokenStore | None = None,
) -> TokenPair:
    """Issue a new token pair from a valid refresh token.

    Rotates the refresh token when ``config.enable_refresh_rotation`` is True.

    Raises:
        TokenExpired: Refresh token expired.
        TokenRevoked: Refresh token revoked.
        InvalidToken: Malformed, wrong type, or user inactive/gone.
    """
    if refresh_token_store is not None and config.enable_refresh_rotation:
        payload = jwt_handler.decode_token(refresh_token, expected_type="refresh")
    else:
        payload = await jwt_handler.verify_token(refresh_token, expected_type="refresh")

    user = await store.get_by_id(payload.sub)
    if user is None or not user.is_active:
        raise InvalidToken("User account is inactive or no longer exists")

    pair = jwt_handler.create_token_pair(
        user.id,
        roles=user.roles,
        scopes=user.scopes,
        session_id=payload.sid,
        family_id=payload.family_id,
    )
    if refresh_token_store is not None:
        replacement = record_from_token(jwt_handler, pair.refresh_token)
        if config.enable_refresh_rotation:
            if not await refresh_token_store.rotate(payload.jti, replacement):
                await jwt_handler.blacklist_jti(
                    payload.jti,
                    max(0, payload.exp - int(time.time())),
                )
                raise TokenRevoked("Refresh token replay detected; token family revoked")
        else:
            if not await refresh_token_store.is_active(payload.jti):
                raise TokenRevoked()
            await refresh_token_store.register(replacement)

    if config.enable_refresh_rotation:
        await jwt_handler.blacklist_token(refresh_token, expected_type="refresh")

    return pair
