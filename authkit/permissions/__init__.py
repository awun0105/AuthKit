"""Retained JWT role/scope helpers from AuthWarden.

Database-backed RBAC lives in ``authkit.authorization``. These helpers operate
on token claims only. ``ROLE_HIERARCHY`` is a compatibility ladder, not a
catalog of business roles.
"""

from authkit.permissions.policies import has_scope, require_scopes, require_superuser
from authkit.permissions.roles import (
    ROLE_HIERARCHY,
    has_min_role,
    has_role,
    require_min_role,
    require_roles,
)

__all__ = [
    "ROLE_HIERARCHY",
    "has_min_role",
    "has_role",
    "has_scope",
    "require_min_role",
    "require_roles",
    "require_scopes",
    "require_superuser",
]
