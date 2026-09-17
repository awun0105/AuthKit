"""Backend bundle that keeps all AuthKit state in memory."""

from authkit.adapters.memory.rbac import MemoryRBACStore
from authkit.audit import MemoryAuditSink
from authkit.authentication.jwt import MemoryTokenBlacklist
from authkit.authentication.oauth_state import MemoryOAuthStateStore
from authkit.session.memory import MemorySessionBackend
from authkit.session.refresh import MemoryRefreshTokenStore
from authkit.storage.memory import MemoryUserStore


class MemoryBackend:
    """Development/test backend; state is process-local and non-durable."""

    def __init__(self) -> None:
        self._users = MemoryUserStore()
        self._rbac = MemoryRBACStore(self._users)
        self._sessions = MemorySessionBackend()
        self._audit = MemoryAuditSink()
        self._token_blacklist = MemoryTokenBlacklist()
        self._oauth_states = MemoryOAuthStateStore()
        self._refresh_tokens = MemoryRefreshTokenStore()

    @property
    def users(self) -> MemoryUserStore:
        return self._users

    @property
    def rbac(self) -> MemoryRBACStore:
        return self._rbac

    @property
    def sessions(self) -> MemorySessionBackend:
        return self._sessions

    @property
    def audit(self) -> MemoryAuditSink:
        return self._audit

    @property
    def token_blacklist(self) -> MemoryTokenBlacklist:
        return self._token_blacklist

    @property
    def oauth_states(self) -> MemoryOAuthStateStore:
        return self._oauth_states

    @property
    def refresh_tokens(self) -> MemoryRefreshTokenStore:
        return self._refresh_tokens
