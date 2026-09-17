"""Async repositories implementing AuthKit's storage ports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from authkit.adapters.sqlalchemy.models import (
    AuditEventORM,
    OAuthAccountORM,
    OAuthStateORM,
    PermissionORM,
    RefreshTokenORM,
    RoleORM,
    SessionORM,
    TokenRevocationORM,
    UserORM,
    role_permissions,
    user_roles,
)
from authkit.audit import AuditEvent
from authkit.authentication.oauth_state import OAuthStateData
from authkit.authorization.models import Permission, Role
from authkit.models.user import OAuthAccount, UserInDB
from authkit.session.base import SessionData
from authkit.session.refresh import RefreshTokenRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class SQLAlchemyUserStore:
    """SQLAlchemy implementation of the core ``AbstractUserStore`` port."""

    _MUTABLE_FIELDS = (
        "email",
        "username",
        "full_name",
        "hashed_password",
        "phone_number",
        "phone_verified",
        "is_active",
        "is_verified",
        "is_superuser",
        "extra_data",
        "mfa_enabled",
        "mfa_secret",
        "mfa_pending_secret",
        "backup_codes",
        "last_verification_sent_at",
        "verification_otp_hash",
        "verification_otp_expires_at",
        "verification_otp_attempts",
        "last_reset_request_at",
        "reset_token_hash",
        "reset_token_used_at",
        "reset_otp_hash",
        "reset_otp_expires_at",
        "reset_otp_attempts",
        "failed_login_attempts",
        "locked_until",
        "created_at",
        "updated_at",
    )

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def _authz(self, session: AsyncSession, user_id: str) -> tuple[list[str], list[str]]:
        role_names = list(
            (
                await session.scalars(
                    select(RoleORM.name)
                    .join(user_roles, RoleORM.id == user_roles.c.role_id)
                    .where(user_roles.c.user_id == user_id)
                    .order_by(RoleORM.name)
                )
            ).all()
        )
        permission_names = list(
            (
                await session.scalars(
                    select(PermissionORM.name)
                    .join(
                        role_permissions,
                        PermissionORM.id == role_permissions.c.permission_id,
                    )
                    .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
                    .where(user_roles.c.user_id == user_id)
                    .distinct()
                    .order_by(PermissionORM.name)
                )
            ).all()
        )
        return role_names, permission_names

    async def _to_domain(self, session: AsyncSession, row: UserORM) -> UserInDB:
        roles, permissions = await self._authz(session, row.id)
        values = {name: getattr(row, name) for name in self._MUTABLE_FIELDS}
        for name, value in values.items():
            if isinstance(value, datetime):
                values[name] = _aware(value)
        return UserInDB(id=row.id, roles=roles, scopes=permissions, **values)

    async def get_by_id(self, user_id: str) -> UserInDB | None:
        async with self._sessions() as session:
            row = await session.get(UserORM, user_id)
            return await self._to_domain(session, row) if row else None

    async def _get_one(self, field: Any, value: str) -> UserInDB | None:
        async with self._sessions() as session:
            row = await session.scalar(select(UserORM).where(field == value))
            return await self._to_domain(session, row) if row else None

    async def get_by_email(self, email: str) -> UserInDB | None:
        return await self._get_one(UserORM.email, email.strip().lower())

    async def get_by_username(self, username: str) -> UserInDB | None:
        return await self._get_one(UserORM.username, username.strip().lower())

    async def get_by_phone(self, phone: str) -> UserInDB | None:
        return await self._get_one(UserORM.phone_number, phone.strip())

    async def create(self, user: UserInDB) -> UserInDB:
        values = {name: getattr(user, name) for name in self._MUTABLE_FIELDS}
        values["email"] = str(user.email).strip().lower()
        values["username"] = user.username.strip().lower() if user.username else None
        async with self._sessions.begin() as session:
            session.add(UserORM(id=user.id, **values))
        created = await self.get_by_id(user.id)
        if created is None:  # pragma: no cover - defensive against external DB triggers
            raise RuntimeError("created AuthKit user could not be reloaded")
        return created

    async def update(self, user: UserInDB) -> UserInDB:
        async with self._sessions.begin() as session:
            row = await session.get(UserORM, user.id)
            if row is None:
                raise KeyError(f"unknown user: {user.id}")
            for name in self._MUTABLE_FIELDS:
                value = getattr(user, name)
                if name == "email":
                    value = str(value).strip().lower()
                elif name == "username" and value:
                    value = value.strip().lower()
                setattr(row, name, value)
        updated = await self.get_by_id(user.id)
        if updated is None:  # pragma: no cover
            raise RuntimeError("updated AuthKit user could not be reloaded")
        return updated

    async def delete(self, user_id: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))

    @staticmethod
    def _oauth_to_domain(row: OAuthAccountORM) -> OAuthAccount:
        return OAuthAccount(
            id=row.id,
            user_id=row.user_id,
            provider=row.provider,
            provider_user_id=row.provider_user_id,
            email=row.email,
            access_token=row.access_token,
            refresh_token=row.refresh_token,
            token_expires_at=_aware(row.token_expires_at) if row.token_expires_at else None,
            created_at=_aware(row.created_at),
            updated_at=_aware(row.updated_at),
        )

    async def get_oauth_account(
        self, provider: str, provider_user_id: str
    ) -> OAuthAccount | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(OAuthAccountORM).where(
                    OAuthAccountORM.provider == provider,
                    OAuthAccountORM.provider_user_id == provider_user_id,
                )
            )
            return self._oauth_to_domain(row) if row else None

    async def get_oauth_accounts_for_user(self, user_id: str) -> list[OAuthAccount]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(OAuthAccountORM)
                    .where(OAuthAccountORM.user_id == user_id)
                    .order_by(OAuthAccountORM.provider)
                )
            ).all()
            return [self._oauth_to_domain(row) for row in rows]

    async def create_oauth_account(self, account: OAuthAccount) -> OAuthAccount:
        async with self._sessions.begin() as session:
            session.add(OAuthAccountORM(**account.model_dump()))
        return account

    async def update_oauth_account(self, account: OAuthAccount) -> OAuthAccount:
        async with self._sessions.begin() as session:
            row = await session.get(OAuthAccountORM, account.id)
            if row is None:
                raise KeyError(f"unknown OAuth account: {account.id}")
            for name, value in account.model_dump().items():
                setattr(row, name, value)
        return account

    async def delete_oauth_account(self, user_id: str, provider: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(OAuthAccountORM).where(
                    OAuthAccountORM.user_id == user_id,
                    OAuthAccountORM.provider == provider,
                )
            )


class SQLAlchemyRBACStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def _role(self, session: AsyncSession, name: str) -> RoleORM | None:
        result = await session.execute(
            select(RoleORM).where(RoleORM.name == name.strip().lower())
        )
        return result.scalar_one_or_none()

    async def _permission(self, session: AsyncSession, name: str) -> PermissionORM | None:
        result = await session.execute(
            select(PermissionORM).where(PermissionORM.name == name.strip().lower())
        )
        return result.scalar_one_or_none()

    async def _to_role(self, session: AsyncSession, row: RoleORM) -> Role:
        permissions = (
            await session.scalars(
                select(PermissionORM)
                .join(
                    role_permissions,
                    PermissionORM.id == role_permissions.c.permission_id,
                )
                .where(role_permissions.c.role_id == row.id)
                .order_by(PermissionORM.name)
            )
        ).all()
        return Role(
            id=row.id,
            name=row.name,
            description=row.description,
            created_at=_aware(row.created_at),
            permissions=[
                Permission(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    created_at=_aware(p.created_at),
                )
                for p in permissions
            ],
        )

    async def create_role(self, role: Role) -> Role:
        async with self._sessions.begin() as session:
            session.add(
                RoleORM(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    created_at=role.created_at,
                )
            )
        created = await self.get_role(role.name)
        assert created is not None
        return created

    async def get_role(self, name: str) -> Role | None:
        async with self._sessions() as session:
            row = await self._role(session, name)
            return await self._to_role(session, row) if row else None

    async def list_roles(self) -> list[Role]:
        async with self._sessions() as session:
            rows = (await session.scalars(select(RoleORM).order_by(RoleORM.name))).all()
            return [await self._to_role(session, row) for row in rows]

    async def delete_role(self, name: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(RoleORM).where(RoleORM.name == name.strip().lower()))

    async def create_permission(self, permission: Permission) -> Permission:
        async with self._sessions.begin() as session:
            session.add(
                PermissionORM(
                    id=permission.id,
                    name=permission.name,
                    description=permission.description,
                    created_at=permission.created_at,
                )
            )
        return permission

    async def get_permission(self, name: str) -> Permission | None:
        async with self._sessions() as session:
            row = await self._permission(session, name)
            if row is None:
                return None
            return Permission(
                id=row.id,
                name=row.name,
                description=row.description,
                created_at=_aware(row.created_at),
            )

    async def list_permissions(self) -> list[Permission]:
        async with self._sessions() as session:
            rows = (await session.scalars(select(PermissionORM).order_by(PermissionORM.name))).all()
            return [
                Permission(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    created_at=_aware(row.created_at),
                )
                for row in rows
            ]

    async def delete_permission(self, name: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(PermissionORM).where(PermissionORM.name == name.strip().lower())
            )

    async def assign_role_to_user(self, user_id: str, role_name: str) -> None:
        async with self._sessions.begin() as session:
            role = await self._role(session, role_name)
            if role is None:
                raise KeyError(f"unknown role: {role_name}")
            if await session.get(UserORM, user_id) is None:
                raise KeyError(f"unknown user: {user_id}")
            exists = await session.scalar(
                select(user_roles.c.user_id).where(
                    user_roles.c.user_id == user_id, user_roles.c.role_id == role.id
                )
            )
            if exists is None:
                await session.execute(insert(user_roles).values(user_id=user_id, role_id=role.id))

    async def remove_role_from_user(self, user_id: str, role_name: str) -> None:
        async with self._sessions.begin() as session:
            role = await self._role(session, role_name)
            if role:
                await session.execute(
                    delete(user_roles).where(
                        user_roles.c.user_id == user_id, user_roles.c.role_id == role.id
                    )
                )

    async def assign_permission_to_role(self, role_name: str, permission_name: str) -> None:
        async with self._sessions.begin() as session:
            role = await self._role(session, role_name)
            permission = await self._permission(session, permission_name)
            if role is None:
                raise KeyError(f"unknown role: {role_name}")
            if permission is None:
                raise KeyError(f"unknown permission: {permission_name}")
            exists = await session.scalar(
                select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role.id,
                    role_permissions.c.permission_id == permission.id,
                )
            )
            if exists is None:
                await session.execute(
                    insert(role_permissions).values(
                        role_id=role.id, permission_id=permission.id
                    )
                )

    async def remove_permission_from_role(self, role_name: str, permission_name: str) -> None:
        async with self._sessions.begin() as session:
            role = await self._role(session, role_name)
            permission = await self._permission(session, permission_name)
            if role and permission:
                await session.execute(
                    delete(role_permissions).where(
                        role_permissions.c.role_id == role.id,
                        role_permissions.c.permission_id == permission.id,
                    )
                )

    async def get_user_roles(self, user_id: str) -> list[Role]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(RoleORM)
                    .join(user_roles, RoleORM.id == user_roles.c.role_id)
                    .where(user_roles.c.user_id == user_id)
                    .order_by(RoleORM.name)
                )
            ).all()
            return [await self._to_role(session, row) for row in rows]

    async def get_user_permissions(self, user_id: str) -> list[Permission]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(PermissionORM)
                    .join(
                        role_permissions,
                        PermissionORM.id == role_permissions.c.permission_id,
                    )
                    .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
                    .where(user_roles.c.user_id == user_id)
                    .distinct()
                    .order_by(PermissionORM.name)
                )
            ).all()
            return [
                Permission(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    created_at=_aware(row.created_at),
                )
                for row in rows
            ]


class SQLAlchemySessionStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @staticmethod
    def _to_domain(row: SessionORM) -> SessionData:
        return SessionData(
            session_id=row.session_id,
            user_id=row.user_id,
            user_agent=row.user_agent,
            ip_hash=row.ip_hash,
            issued_at=_aware(row.issued_at),
            expires_at=_aware(row.expires_at),
        )

    async def create(self, session_data: SessionData) -> SessionData:
        async with self._sessions.begin() as session:
            session.add(SessionORM(**session_data.model_dump()))
        return session_data

    async def get(self, session_id: str) -> SessionData | None:
        async with self._sessions.begin() as session:
            row = await session.get(SessionORM, session_id)
            if row is None:
                return None
            if _aware(row.expires_at) <= _now():
                await session.delete(row)
                return None
            return self._to_domain(row)

    async def delete(self, session_id: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(SessionORM).where(SessionORM.session_id == session_id))

    async def delete_all_for_user(self, user_id: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(SessionORM).where(SessionORM.user_id == user_id))

    async def get_all_for_user(self, user_id: str) -> list[SessionData]:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(SessionORM).where(
                    SessionORM.user_id == user_id, SessionORM.expires_at <= _now()
                )
            )
            rows = (
                await session.scalars(
                    select(SessionORM)
                    .where(SessionORM.user_id == user_id)
                    .order_by(SessionORM.issued_at.desc())
                )
            ).all()
            return [self._to_domain(row) for row in rows]


class SQLAlchemyTokenBlacklist:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, jti: str, ttl_seconds: int) -> None:
        expires_at = _now() + timedelta(seconds=max(1, ttl_seconds))
        async with self._sessions.begin() as session:
            existing = await session.get(TokenRevocationORM, jti)
            if existing:
                existing.expires_at = expires_at
            else:
                session.add(TokenRevocationORM(jti=jti, expires_at=expires_at))

    async def contains(self, jti: str) -> bool:
        async with self._sessions.begin() as session:
            row = await session.get(TokenRevocationORM, jti)
            if row is None:
                return False
            if _aware(row.expires_at) <= _now():
                await session.delete(row)
                return False
            return True


class SQLAlchemyRefreshTokenStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def register(self, record: RefreshTokenRecord) -> None:
        async with self._sessions.begin() as session:
            session.add(RefreshTokenORM(**record.model_dump(), revoked_at=None, replaced_by_jti=None))

    async def is_active(self, jti: str) -> bool:
        async with self._sessions() as session:
            row = await session.get(RefreshTokenORM, jti)
            return bool(
                row
                and row.revoked_at is None
                and _aware(row.expires_at) > _now()
            )

    async def rotate(self, current_jti: str, replacement: RefreshTokenRecord) -> bool:
        async with self._sessions.begin() as session:
            current = await session.scalar(
                select(RefreshTokenORM)
                .where(RefreshTokenORM.jti == current_jti)
                .with_for_update()
            )
            if current is None:
                return False
            if current.revoked_at is not None or _aware(current.expires_at) <= _now():
                rows = (
                    await session.scalars(
                        select(RefreshTokenORM)
                        .where(RefreshTokenORM.family_id == current.family_id)
                        .with_for_update()
                    )
                ).all()
                for row in rows:
                    row.revoked_at = row.revoked_at or _now()
                return False
            if replacement.family_id != current.family_id:
                return False
            current.revoked_at = _now()
            current.replaced_by_jti = replacement.jti
            session.add(
                RefreshTokenORM(
                    **replacement.model_dump(),
                    revoked_at=None,
                    replaced_by_jti=None,
                )
            )
            return True

    async def revoke(self, jti: str) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(RefreshTokenORM, jti)
            if row and row.revoked_at is None:
                row.revoked_at = _now()

    async def revoke_all_for_user(self, user_id: str) -> None:
        async with self._sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(RefreshTokenORM).where(
                        RefreshTokenORM.user_id == user_id,
                        RefreshTokenORM.revoked_at.is_(None),
                    )
                )
            ).all()
            for row in rows:
                row.revoked_at = _now()


class SQLAlchemyOAuthStateStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, data: OAuthStateData, ttl_seconds: int = 600) -> None:
        async with self._sessions.begin() as session:
            session.add(
                OAuthStateORM(
                    **data.model_dump(),
                    expires_at=_now() + timedelta(seconds=ttl_seconds),
                )
            )

    async def get_and_delete(self, state: str) -> OAuthStateData | None:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(OAuthStateORM).where(OAuthStateORM.state == state).with_for_update()
            )
            if row is None:
                return None
            await session.delete(row)
            if _aware(row.expires_at) <= _now():
                return None
            return OAuthStateData(
                state=row.state,
                code_verifier=row.code_verifier,
                provider=row.provider,
                purpose=row.purpose,  # type: ignore[arg-type]
                user_id=row.user_id,
                created_at=_aware(row.created_at),
            )


class SQLAlchemyAuditSink:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def write(self, event: AuditEvent) -> None:
        async with self._sessions.begin() as session:
            session.add(AuditEventORM(**event.model_dump()))
