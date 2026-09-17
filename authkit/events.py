"""Lightweight in-process lifecycle events."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AuthEvent(BaseModel):
    """A meaningful AuthKit state transition exposed to consumers."""

    name: str
    user_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class EventSink(Protocol):
    async def publish(self, event: AuthEvent) -> None: ...


class InProcessEventBus:
    """Small async event bus; it is not a broker or delivery guarantee."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[AuthEvent], Awaitable[None]]]] = {}

    def subscribe(
        self,
        event_name: str,
        handler: Callable[[AuthEvent], Awaitable[None]],
    ) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    async def publish(self, event: AuthEvent) -> None:
        handlers = [
            *self._handlers.get(event.name, []),
            *self._handlers.get("*", []),
        ]
        for handler in handlers:
            await handler(event)
