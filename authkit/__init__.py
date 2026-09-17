"""AuthKit — reusable FastAPI authentication and authorization.

    from authkit import AuthKit, AuthKitConfig
    from authkit.adapters.memory import MemoryBackend

    auth = AuthKit(
        config=AuthKitConfig(secret_key="replace-with-at-least-32-random-bytes"),
        backend=MemoryBackend(),
    )
    app.include_router(auth.router, prefix="/auth")
"""
from authkit.core.config import AuthKitConfig, OAuthProviderConfig
from authkit.core.manager import AuthKit
from authkit.exceptions import AuthError
from authkit.gateway import AuthGateway, AuthUser
from authkit.models.token import LogoutRequest, RefreshTokenRequest, TokenPair, TokenPayload
from authkit.models.user import (
    OAuthAccount,
    OAuthAccountRead,
    OAuthUserInfo,
    UserCreate,
    UserInDB,
    UserRead,
)
from authkit.storage.base import AbstractUserStore
from authkit.storage.memory import MemoryUserStore

__version__ = "1.0.0"

__all__ = [
    "AuthKit",
    "AuthKitConfig",
    "AuthGateway",
    "AuthUser",
    "OAuthProviderConfig",
    "AuthError",
    "UserCreate",
    "UserRead",
    "UserInDB",
    "OAuthAccount",
    "OAuthAccountRead",
    "OAuthUserInfo",
    "TokenPair",
    "TokenPayload",
    "RefreshTokenRequest",
    "LogoutRequest",
    "AbstractUserStore",
    "MemoryUserStore",
]
