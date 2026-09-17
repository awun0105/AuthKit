"""Optional, superuser-protected RBAC management router."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from authkit.audit import AuditEvent, AuditSink
from authkit.authorization.models import Permission, Role
from authkit.authorization.protocols import RBACStore
from authkit.events import AuthEvent, EventSink
from authkit.models.user import UserInDB


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class PermissionCreate(BaseModel):
    name: str
    description: str | None = None


async def _not_found(operation) -> None:
    try:
        await operation
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def build_admin_router(
    *,
    rbac: RBACStore,
    get_current_user: Callable,
    audit: AuditSink,
    events: EventSink,
) -> APIRouter:
    async def require_superuser(user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser required")
        return user

    router = APIRouter(
        prefix="/admin",
        tags=["authkit-admin"],
        dependencies=[Depends(require_superuser)],
    )

    @router.post("/roles", response_model=Role, status_code=201)
    async def create_role(data: RoleCreate) -> Role:
        try:
            return await rbac.create_role(Role(name=data.name, description=data.description))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.get("/roles", response_model=list[Role])
    async def list_roles() -> list[Role]:
        return await rbac.list_roles()

    @router.delete("/roles/{role_name}", status_code=204)
    async def delete_role(role_name: str) -> Response:
        await rbac.delete_role(role_name)
        return Response(status_code=204)

    @router.post("/permissions", response_model=Permission, status_code=201)
    async def create_permission(data: PermissionCreate) -> Permission:
        try:
            return await rbac.create_permission(
                Permission(name=data.name, description=data.description)
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.get("/permissions", response_model=list[Permission])
    async def list_permissions() -> list[Permission]:
        return await rbac.list_permissions()

    @router.delete("/permissions/{permission_name}", status_code=204)
    async def delete_permission(permission_name: str) -> Response:
        await rbac.delete_permission(permission_name)
        return Response(status_code=204)

    @router.put("/roles/{role_name}/permissions/{permission_name}", status_code=204)
    async def assign_permission(role_name: str, permission_name: str) -> Response:
        await _not_found(rbac.assign_permission_to_role(role_name, permission_name))
        await audit.write(
            AuditEvent(
                action="permission.assigned",
                details={"role": role_name, "permission": permission_name},
            )
        )
        return Response(status_code=204)

    @router.delete("/roles/{role_name}/permissions/{permission_name}", status_code=204)
    async def remove_permission(role_name: str, permission_name: str) -> Response:
        await rbac.remove_permission_from_role(role_name, permission_name)
        await audit.write(
            AuditEvent(
                action="permission.removed",
                details={"role": role_name, "permission": permission_name},
            )
        )
        return Response(status_code=204)

    @router.put("/users/{user_id}/roles/{role_name}", status_code=204)
    async def assign_role(user_id: str, role_name: str) -> Response:
        await _not_found(rbac.assign_role_to_user(user_id, role_name))
        await audit.write(
            AuditEvent(
                action="role.assigned",
                user_id=user_id,
                details={"role": role_name},
            )
        )
        await events.publish(AuthEvent(name="RoleAssigned", user_id=user_id, data={"role": role_name}))
        return Response(status_code=204)

    @router.delete("/users/{user_id}/roles/{role_name}", status_code=204)
    async def remove_role(user_id: str, role_name: str) -> Response:
        await rbac.remove_role_from_user(user_id, role_name)
        await audit.write(
            AuditEvent(
                action="role.removed",
                user_id=user_id,
                details={"role": role_name},
            )
        )
        await events.publish(AuthEvent(name="RoleRemoved", user_id=user_id, data={"role": role_name}))
        return Response(status_code=204)

    return router
