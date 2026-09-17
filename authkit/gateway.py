"""ORM-free public gateway for cross-module identity lookups."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from authkit.storage.base import AbstractUserStore


class AuthUser(BaseModel):
    """Minimal public identity DTO safe for business-module consumption."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str | None = None
    full_name: str | None = None
    is_active: bool
    is_verified: bool
    roles: list[str]
    permissions: list[str]


@runtime_checkable
class AuthGatewayProtocol(Protocol):
    async def get_user(self, user_id: str) -> AuthUser | None: ...


class AuthGateway:
    """Default gateway backed only by the core user-store protocol."""

    def __init__(self, store: AbstractUserStore) -> None:
        self._store = store

    async def get_user(self, user_id: str) -> AuthUser | None:
        user = await self._store.get_by_id(user_id)
        if user is None:
            return None
        return AuthUser(
            id=user.id,
            email=str(user.email),
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=list(user.roles),
            permissions=list(user.scopes),
        )
