"""Public role and permission DTOs.

Roles are application data. AuthKit never defines business-specific role names.
Permissions follow ``<resource>.<action>`` and are otherwise unrestricted.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PERMISSION_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*\.[a-z0-9][a-z0-9_-]*$")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def validate_permission_name(value: str) -> str:
    """Validate and normalize an AuthKit permission name."""
    normalized = value.strip().lower()
    if not _PERMISSION_RE.fullmatch(normalized):
        raise ValueError("permission must use the '<resource>.<action>' convention")
    return normalized


class Permission(BaseModel):
    """A consumer-defined permission such as ``documents.create``."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=_uuid)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=_now)

    _normalize_name = field_validator("name")(validate_permission_name)


class Role(BaseModel):
    """A consumer-defined role containing zero or more permissions."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=_uuid)
    name: str
    description: str | None = None
    permissions: list[Permission] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("role name must not be empty")
        if len(normalized) > 100:
            raise ValueError("role name must be at most 100 characters")
        return normalized
