"""Persistent refresh-token family contracts.

Only JWT identifiers and metadata are stored; raw refresh tokens are never
persisted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from authkit.authentication.jwt import JWTHandler


class RefreshTokenRecord(BaseModel):
    jti: str
    family_id: str
    user_id: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def record_from_token(jwt_handler: JWTHandler, token: str) -> RefreshTokenRecord:
    payload = jwt_handler.decode_token(token, expected_type="refresh")
    if not payload.family_id:
        raise ValueError("refresh token is missing its family identifier")
    return RefreshTokenRecord(
        jti=payload.jti,
        family_id=payload.family_id,
        user_id=payload.sub,
        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
        created_at=datetime.fromtimestamp(payload.iat, tz=timezone.utc),
    )


@runtime_checkable
class RefreshTokenStore(Protocol):
    async def register(self, record: RefreshTokenRecord) -> None: ...

    async def is_active(self, jti: str) -> bool: ...

    async def rotate(self, current_jti: str, replacement: RefreshTokenRecord) -> bool:
        """Atomically consume a token and insert its replacement.

        Returns false for missing/replayed tokens. Implementations must revoke
        the full family when a consumed token is replayed.
        """
        ...

    async def revoke(self, jti: str) -> None: ...

    async def revoke_all_for_user(self, user_id: str) -> None: ...


class MemoryRefreshTokenStore:
    def __init__(self) -> None:
        self._records: dict[str, RefreshTokenRecord] = {}
        self._revoked: set[str] = set()

    async def register(self, record: RefreshTokenRecord) -> None:
        self._records[record.jti] = record.model_copy(deep=True)

    async def is_active(self, jti: str) -> bool:
        record = self._records.get(jti)
        return bool(
            record
            and jti not in self._revoked
            and record.expires_at > datetime.now(timezone.utc)
        )

    async def rotate(self, current_jti: str, replacement: RefreshTokenRecord) -> bool:
        current = self._records.get(current_jti)
        if current is None:
            return False
        if current_jti in self._revoked or current.expires_at <= datetime.now(timezone.utc):
            self._revoked.update(
                record.jti
                for record in self._records.values()
                if record.family_id == current.family_id
            )
            return False
        if replacement.family_id != current.family_id:
            return False
        self._revoked.add(current_jti)
        self._records[replacement.jti] = replacement.model_copy(deep=True)
        return True

    async def revoke(self, jti: str) -> None:
        if jti in self._records:
            self._revoked.add(jti)

    async def revoke_all_for_user(self, user_id: str) -> None:
        self._revoked.update(
            record.jti for record in self._records.values() if record.user_id == user_id
        )
