from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine, inspect, select

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.sqlalchemy import SQLAlchemyBackend
from authkit.adapters.sqlalchemy.models import AuditEventORM
from authkit.authorization.models import Permission, Role
from authkit.migrations import upgrade

SECRET = "authkit-test-secret-at-least-32-bytes-long"


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'authkit.db'}"


@pytest.fixture
def migrated_database_url(database_url: str) -> str:
    upgrade(database_url)
    return database_url


def test_migration_from_empty_database_is_repeatable(database_url: str) -> None:
    upgrade(database_url)
    upgrade(database_url)
    engine = create_engine(database_url.replace("+aiosqlite", ""))
    try:
        tables = set(inspect(engine).get_table_names())
        assert "authkit_users" in tables
        assert "authkit_roles" in tables
        assert "authkit_permissions" in tables
        assert "authkit_alembic_version" in tables
        assert "users" not in tables
        version = engine.connect().exec_driver_sql(
            "select version_num from authkit_alembic_version"
        ).scalar_one()
        assert version == "0001_authkit"
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_sqlalchemy_backend_rbac_and_gateway(migrated_database_url: str) -> None:
    backend = SQLAlchemyBackend(migrated_database_url)
    auth = AuthKit(
        AuthKitConfig(secret_key=SECRET, require_email_verification=False),
        backend=backend,
    )
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")

    @app.get("/documents", dependencies=[Depends(auth.require_permission("documents.read"))])
    async def documents() -> dict[str, bool]:
        return {"allowed": True}

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            registered = await client.post(
                "/auth/register",
                json={"email": "reader@example.com", "password": "password123"},
            )
            assert registered.status_code == 201, registered.text
            user_id = registered.json()["id"]

            await backend.rbac.create_role(Role(name="reader"))
            await backend.rbac.create_permission(Permission(name="documents.read"))
            await backend.rbac.assign_permission_to_role("reader", "documents.read")
            await backend.rbac.assign_role_to_user(user_id, "reader")

            login = await client.post(
                "/auth/login",
                json={"identifier": "reader@example.com", "password": "password123"},
            )
            assert login.status_code == 200, login.text
            tokens = login.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            assert (await client.get("/documents", headers=headers)).status_code == 200

            identity = await auth.gateway.get_user(user_id)
            assert identity is not None
            assert identity.roles == ["reader"]
            assert identity.permissions == ["documents.read"]

            access_payload = auth.jwt_handler.decode_token(tokens["access_token"])
            assert access_payload.sid is not None
            assert await backend.sessions.get(access_payload.sid) is not None

            rotated = await client.post(
                "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            )
            assert rotated.status_code == 200, rotated.text
            rotated_refresh = rotated.json()["refresh_token"]
            replay = await client.post(
                "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            )
            assert replay.status_code == 401
            family_rejected = await client.post(
                "/auth/refresh", json={"refresh_token": rotated_refresh}
            )
            assert family_rejected.status_code == 401

            logout = await client.post(
                "/auth/logout",
                headers=headers,
                json={"refresh_token": tokens["refresh_token"]},
            )
            assert logout.status_code == 204, logout.text
            assert await backend.sessions.get(access_payload.sid) is None
            rejected = await client.post(
                "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            )
            assert rejected.status_code == 401

        async with backend.session_factory() as session:
            actions = list(await session.scalars(select(AuditEventORM.action)))
        assert "user.registered" in actions
        assert "user.login_succeeded" in actions
        assert "user.logout" in actions
    finally:
        await backend.close()


@pytest.mark.asyncio
async def test_admin_router_is_disabled_by_default(migrated_database_url: str) -> None:
    backend = SQLAlchemyBackend(migrated_database_url)
    try:
        auth = AuthKit(AuthKitConfig(secret_key=SECRET), backend=backend)
        app = FastAPI()
        app.include_router(auth.router, prefix="/auth")
        paths = set(app.openapi()["paths"])
        assert not any(path.startswith("/auth/admin") for path in paths)
    finally:
        await backend.close()


def test_config_environment_loading_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHKIT_SECRET_KEY", SECRET)
    with pytest.raises(Exception):
        AuthKitConfig()
    assert AuthKitConfig.from_env().secret_key == SECRET


def test_cli_create_admin_is_explicit(database_url: str, capsys: pytest.CaptureFixture[str]) -> None:
    from authkit.cli import main

    main(["db", "upgrade", "--database-url", database_url])
    main(
        [
            "create-admin",
            "--database-url",
            database_url,
            "--secret-key",
            SECRET,
            "--email",
            "admin@example.com",
            "--password",
            "password123",
        ]
    )
    assert "administrator ready" in capsys.readouterr().out

    async def verify() -> None:
        backend = SQLAlchemyBackend(database_url)
        try:
            user = await backend.users.get_by_email("admin@example.com")
            assert user is not None
            assert user.is_superuser is True
            assert user.is_verified is True
        finally:
            await backend.close()

    asyncio.run(verify())


def test_oauth_and_mfa_disabled_startup() -> None:
    from authkit.adapters.memory import MemoryBackend

    auth = AuthKit(AuthKitConfig(secret_key=SECRET), backend=MemoryBackend())
    assert auth.config.enable_mfa is False
    assert auth.oauth_providers == {}


@pytest.mark.asyncio
async def test_admin_router_requires_explicit_enable_and_superuser() -> None:
    from authkit.adapters.memory import MemoryBackend
    from authkit.models.user import UserInDB

    backend = MemoryBackend()
    config = AuthKitConfig(
        secret_key=SECRET,
        require_email_verification=False,
        enable_admin_router=True,
    )
    auth = AuthKit(config, backend=backend)
    regular = await backend.users.create(
        UserInDB(
            email="regular@example.com",
            hashed_password=auth.password_handler.hash_password("password123"),
            is_verified=True,
            is_active=True,
        )
    )
    admin = await backend.users.create(
        UserInDB(
            email="root@example.com",
            hashed_password=auth.password_handler.hash_password("password123"),
            is_verified=True,
            is_active=True,
            is_superuser=True,
        )
    )
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async def token_for(email: str) -> str:
            response = await client.post(
                "/auth/login", json={"identifier": email, "password": "password123"}
            )
            assert response.status_code == 200
            return response.json()["access_token"]

        regular_token = await token_for(str(regular.email))
        denied = await client.post(
            "/auth/admin/roles",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"name": "editor"},
        )
        assert denied.status_code == 403

        admin_token = await token_for(str(admin.email))
        headers = {"Authorization": f"Bearer {admin_token}"}
        created = await client.post(
            "/auth/admin/roles", headers=headers, json={"name": "editor"}
        )
        assert created.status_code == 201, created.text
        permission = await client.post(
            "/auth/admin/permissions",
            headers=headers,
            json={"name": "documents.create"},
        )
        assert permission.status_code == 201, permission.text
        assigned = await client.put(
            "/auth/admin/roles/editor/permissions/documents.create", headers=headers
        )
        assert assigned.status_code == 204
        user_role = await client.put(
            f"/auth/admin/users/{regular.id}/roles/editor", headers=headers
        )
        assert user_role.status_code == 204
        updated = await backend.users.get_by_id(regular.id)
        assert updated is not None
        assert updated.roles == ["editor"]
        assert updated.scopes == ["documents.create"]


@pytest.mark.asyncio
@pytest.mark.postgres
@pytest.mark.skipif(
    not os.environ.get("AUTHKIT_TEST_POSTGRES_URL"),
    reason="AUTHKIT_TEST_POSTGRES_URL is not configured",
)
async def test_postgres_migrations_and_adapter() -> None:
    database_url = os.environ["AUTHKIT_TEST_POSTGRES_URL"]
    await asyncio.to_thread(upgrade, database_url)
    backend = SQLAlchemyBackend(database_url)
    try:
        from authkit.models.user import UserInDB

        user = await backend.users.create(
            UserInDB(email="postgres@example.com", hashed_password="not-a-real-hash")
        )
        await backend.rbac.create_role(Role(name="postgres-reader"))
        await backend.rbac.create_permission(Permission(name="postgres.read"))
        await backend.rbac.assign_permission_to_role("postgres-reader", "postgres.read")
        await backend.rbac.assign_role_to_user(user.id, "postgres-reader")
        loaded = await backend.users.get_by_id(user.id)
        assert loaded is not None
        assert loaded.roles == ["postgres-reader"]
        assert loaded.scopes == ["postgres.read"]
    finally:
        await backend.close()
