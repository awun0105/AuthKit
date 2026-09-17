"""In-memory RBAC store."""

from __future__ import annotations

from authkit.authorization.models import Permission, Role
from authkit.storage.memory import MemoryUserStore


class MemoryRBACStore:
    def __init__(self, users: MemoryUserStore | None = None) -> None:
        self._users = users
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}
        self._user_roles: dict[str, set[str]] = {}
        self._role_permissions: dict[str, set[str]] = {}

    async def _sync_user(self, user_id: str) -> None:
        if self._users is None:
            return
        user = await self._users.get_by_id(user_id)
        if user is None:
            return
        user.roles = sorted(self._user_roles.get(user_id, set()))
        permission_names: set[str] = set()
        for role_name in user.roles:
            permission_names.update(self._role_permissions.get(role_name, set()))
        user.scopes = sorted(permission_names)
        await self._users.update(user)

    async def _sync_role_users(self, role_name: str) -> None:
        for user_id, roles in self._user_roles.items():
            if role_name in roles:
                await self._sync_user(user_id)

    async def create_role(self, role: Role) -> Role:
        if role.name in self._roles:
            raise ValueError(f"role already exists: {role.name}")
        self._roles[role.name] = role.model_copy(deep=True)
        self._role_permissions[role.name] = {p.name for p in role.permissions}
        return await self._hydrate_role(role.name)

    async def get_role(self, name: str) -> Role | None:
        key = name.strip().lower()
        if key not in self._roles:
            return None
        return await self._hydrate_role(key)

    async def _hydrate_role(self, name: str) -> Role:
        role = self._roles[name].model_copy(deep=True)
        role.permissions = [
            self._permissions[p].model_copy(deep=True)
            for p in sorted(self._role_permissions.get(name, set()))
            if p in self._permissions
        ]
        return role

    async def list_roles(self) -> list[Role]:
        return [await self._hydrate_role(name) for name in sorted(self._roles)]

    async def delete_role(self, name: str) -> None:
        key = name.strip().lower()
        self._roles.pop(key, None)
        self._role_permissions.pop(key, None)
        for roles in self._user_roles.values():
            roles.discard(key)
        for user_id in self._user_roles:
            await self._sync_user(user_id)

    async def create_permission(self, permission: Permission) -> Permission:
        if permission.name in self._permissions:
            raise ValueError(f"permission already exists: {permission.name}")
        self._permissions[permission.name] = permission.model_copy(deep=True)
        return permission.model_copy(deep=True)

    async def get_permission(self, name: str) -> Permission | None:
        permission = self._permissions.get(name.strip().lower())
        return permission.model_copy(deep=True) if permission else None

    async def list_permissions(self) -> list[Permission]:
        return [self._permissions[name].model_copy(deep=True) for name in sorted(self._permissions)]

    async def delete_permission(self, name: str) -> None:
        key = name.strip().lower()
        self._permissions.pop(key, None)
        for permissions in self._role_permissions.values():
            permissions.discard(key)
        for user_id in self._user_roles:
            await self._sync_user(user_id)

    async def assign_role_to_user(self, user_id: str, role_name: str) -> None:
        key = role_name.strip().lower()
        if key not in self._roles:
            raise KeyError(f"unknown role: {role_name}")
        self._user_roles.setdefault(user_id, set()).add(key)
        await self._sync_user(user_id)

    async def remove_role_from_user(self, user_id: str, role_name: str) -> None:
        self._user_roles.get(user_id, set()).discard(role_name.strip().lower())
        await self._sync_user(user_id)

    async def assign_permission_to_role(self, role_name: str, permission_name: str) -> None:
        role_key = role_name.strip().lower()
        permission_key = permission_name.strip().lower()
        if role_key not in self._roles:
            raise KeyError(f"unknown role: {role_name}")
        if permission_key not in self._permissions:
            raise KeyError(f"unknown permission: {permission_name}")
        self._role_permissions.setdefault(role_key, set()).add(permission_key)
        await self._sync_role_users(role_key)

    async def remove_permission_from_role(self, role_name: str, permission_name: str) -> None:
        self._role_permissions.get(role_name.strip().lower(), set()).discard(
            permission_name.strip().lower()
        )
        await self._sync_role_users(role_name.strip().lower())

    async def get_user_roles(self, user_id: str) -> list[Role]:
        return [
            await self._hydrate_role(name)
            for name in sorted(self._user_roles.get(user_id, set()))
            if name in self._roles
        ]

    async def get_user_permissions(self, user_id: str) -> list[Permission]:
        names: set[str] = set()
        for role_name in self._user_roles.get(user_id, set()):
            names.update(self._role_permissions.get(role_name, set()))
        return [
            self._permissions[name].model_copy(deep=True)
            for name in sorted(names)
            if name in self._permissions
        ]
