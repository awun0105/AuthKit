"""Optional security-audit port, independent from application logging."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Append-only security event passed to an ``AuditSink``."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    user_id: str | None = None
    actor_user_id: str | None = None
    ip_hash: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class AuditSink(Protocol):
    """Port for append-only security audit persistence."""

    async def write(self, event: AuditEvent) -> None: ...


class NullAuditSink:
    """Default sink for consumers that do not want audit persistence."""

    async def write(self, event: AuditEvent) -> None:
        del event


class MemoryAuditSink:
    """Deterministic development/test audit sink."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event.model_copy(deep=True))
