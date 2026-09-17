"""Composition contract for official and custom AuthKit backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from authkit.audit import AuditSink
from authkit.authentication.jwt import AbstractTokenBlacklist
from authkit.authentication.oauth_state import AbstractOAuthStateStore
from authkit.authorization.protocols import RBACStore
from authkit.session.base import AbstractSessionBackend
from authkit.session.refresh import RefreshTokenStore
from authkit.storage.base import AbstractUserStore


@runtime_checkable
class AuthBackend(Protocol):
    """A bundle of storage ports used by the public ``AuthKit`` facade.

    A backend is a composition root, not a mega-repository: each property is a
    narrow protocol and can be implemented by a different technology.
    """

    @property
    def users(self) -> AbstractUserStore: ...

    @property
    def rbac(self) -> RBACStore | None: ...

    @property
    def sessions(self) -> AbstractSessionBackend | None: ...

    @property
    def audit(self) -> AuditSink | None: ...

    @property
    def token_blacklist(self) -> AbstractTokenBlacklist | None: ...

    @property
    def oauth_states(self) -> AbstractOAuthStateStore | None: ...

    @property
    def refresh_tokens(self) -> RefreshTokenStore | None: ...
