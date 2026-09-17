"""Storage-agnostic role and permission contracts."""

from authkit.authorization.models import Permission, Role
from authkit.authorization.protocols import RBACStore

__all__ = ["Permission", "RBACStore", "Role"]
