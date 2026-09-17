"""Logout flow."""
from __future__ import annotations

from authkit.authentication.jwt import JWTHandler
from authkit.session.base import AbstractSessionBackend
from authkit.session.refresh import RefreshTokenStore


async def logout_flow(
    access_token: str,
    *,
    jwt_handler: JWTHandler,
    refresh_token: str | None = None,
    session_backend: AbstractSessionBackend | None = None,
    session_id: str | None = None,
    refresh_token_store: RefreshTokenStore | None = None,
) -> None:
    """Revoke tokens and destroy session.

    Args:
        access_token:    Bearer token from Authorization header.
        jwt_handler:     JWT handler (holds the blacklist).
        refresh_token:   Optional refresh token to also revoke.
        session_backend: Optional session backend.
        session_id:      Session to destroy.
    """
    await jwt_handler.blacklist_token(access_token, expected_type="access")
    if refresh_token:
        try:
            refresh_payload = jwt_handler.decode_token(refresh_token, expected_type="refresh")
            await jwt_handler.blacklist_token(refresh_token, expected_type="refresh")
            if refresh_token_store is not None:
                await refresh_token_store.revoke(refresh_payload.jti)
        except Exception:
            pass  # already expired — not a hard failure
    if session_backend is not None and session_id is not None:
        await session_backend.delete(session_id)
