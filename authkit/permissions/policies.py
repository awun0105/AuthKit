"""Scope-based permission guards for authkit."""
from __future__ import annotations

from authkit.exceptions import ForbiddenError
from authkit.models.token import TokenPayload


def has_scope(payload: TokenPayload, *required_scopes: str, require_all: bool = False) -> bool:
    """Check whether the token payload satisfies scope requirements.

    Args:
        payload:         Decoded JWT payload containing scopes.
        required_scopes: Scopes to check.
        require_all:     If True, all scopes must be present.
                         If False (default), any one scope is sufficient.

    Returns:
        True if the requirement is satisfied.
    """
    if require_all:
        return all(s in payload.scopes for s in required_scopes)
    return any(s in payload.scopes for s in required_scopes)


def require_scopes(payload: TokenPayload, *scopes: str, require_all: bool = False) -> None:
    """Assert that the token payload satisfies scope requirements.

    Raises:
        ForbiddenError: If the scope check fails.
    """
    if not has_scope(payload, *scopes, require_all=require_all):
        raise ForbiddenError(
            f"Required scope(s): {', '.join(scopes)}. "
            f"Token has: {', '.join(payload.scopes) or 'none'}."
        )


def require_superuser(payload: TokenPayload) -> None:
    """Assert the token carries the retained ``superadmin`` JWT role.

    Official administration uses ``UserInDB.is_superuser``, not this helper.
    """
    if "superadmin" not in payload.roles:
        raise ForbiddenError("Superuser access required.")