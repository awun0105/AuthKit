"""Public-API consumer coverage.

These tests import only the documented integration surface. They do not
import SQLAlchemy ORM models or adapter repository internals.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import httpx
import pytest
from fastapi import Depends, FastAPI

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend
from authkit.authorization import Permission, Role

SECRET = "authkit-e2e-secret-at-least-32-bytes-long"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_public_api_register_login_permission_refresh_logout() -> None:
    backend = MemoryBackend()
    auth = AuthKit(
        AuthKitConfig(secret_key=SECRET, require_email_verification=False),
        backend=backend,
    )
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")

    @app.get("/me")
    async def me(user=Depends(auth.current_user)):
        return {"id": user.id, "email": user.email}

    @app.get(
        "/documents",
        dependencies=[Depends(auth.require_permission("documents.read"))],
    )
    async def documents():
        return {"ok": True}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        registered = await client.post(
            "/auth/register",
            json={"email": "consumer@example.com", "password": "password123"},
        )
        assert registered.status_code == 201, registered.text
        user_id = registered.json()["id"]

        login = await client.post(
            "/auth/login",
            headers={"User-Agent": "AuthKit-E2E/1.0", "X-Forwarded-For": "203.0.113.10"},
            json={"identifier": "consumer@example.com", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        tokens = login.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        me_response = await client.get("/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "consumer@example.com"

        denied = await client.get("/documents", headers=headers)
        assert denied.status_code == 403

        await backend.rbac.create_role(Role(name="reader"))
        await backend.rbac.create_permission(Permission(name="documents.read"))
        await backend.rbac.assign_permission_to_role("reader", "documents.read")
        await backend.rbac.assign_role_to_user(user_id, "reader")

        relogin = await client.post(
            "/auth/login",
            json={"identifier": "consumer@example.com", "password": "password123"},
        )
        assert relogin.status_code == 200
        fresh = relogin.json()
        allowed_headers = {"Authorization": f"Bearer {fresh['access_token']}"}
        allowed = await client.get("/documents", headers=allowed_headers)
        assert allowed.status_code == 200

        identity = await auth.gateway.get_user(user_id)
        assert identity is not None
        assert identity.roles == ["reader"]
        assert identity.permissions == ["documents.read"]

        sessions = await backend.sessions.get_all_for_user(user_id)
        assert sessions
        assert any(session.user_agent == "AuthKit-E2E/1.0" for session in sessions)
        assert any(session.ip_hash for session in sessions)

        rotated = await client.post(
            "/auth/refresh", json={"refresh_token": fresh["refresh_token"]}
        )
        assert rotated.status_code == 200, rotated.text
        replay = await client.post(
            "/auth/refresh", json={"refresh_token": fresh["refresh_token"]}
        )
        assert replay.status_code == 401

        logout = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
            json={"refresh_token": rotated.json()["refresh_token"]},
        )
        assert logout.status_code == 204
        rejected = await client.post(
            "/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        )
        assert rejected.status_code == 401

        user = await backend.users.get_by_id(user_id)
        assert user is not None
        user.is_active = False
        await backend.users.update(user)
        disabled = await client.post(
            "/auth/login",
            json={"identifier": "consumer@example.com", "password": "password123"},
        )
        assert disabled.status_code == 403


@pytest.mark.e2e
def test_clean_install_sqlite_consumer(tmp_path: Path) -> None:
    python = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin") / "python"
    script = tmp_path / "consumer.py"
    script.write_text(
        textwrap.dedent(
            """
            import asyncio
            from pathlib import Path

            import httpx
            from fastapi import Depends, FastAPI

            from authkit import AuthKit, AuthKitConfig
            from authkit.adapters.sqlalchemy import SQLAlchemyBackend
            from authkit.authorization import Permission, Role
            from authkit.migrations import upgrade

            SECRET = "authkit-clean-install-secret-32bytes"
            database_url = "sqlite+aiosqlite:///" + str(Path("authkit.db").resolve())
            upgrade(database_url)

            async def main() -> None:
                backend = SQLAlchemyBackend(database_url)
                try:
                    auth = AuthKit(
                        AuthKitConfig(secret_key=SECRET, require_email_verification=False),
                        backend=backend,
                    )
                    app = FastAPI()
                    app.include_router(auth.router, prefix="/auth")

                    @app.get("/me")
                    async def me(user=Depends(auth.current_user)):
                        return {"id": user.id}

                    @app.post(
                        "/documents",
                        dependencies=[Depends(auth.require_permission("documents.create"))],
                    )
                    async def create_document():
                        return {"created": True}

                    transport = httpx.ASGITransport(app=app)
                    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                        registered = await client.post(
                            "/auth/register",
                            json={"email": "clean@example.com", "password": "password123"},
                        )
                        assert registered.status_code == 201, registered.text
                        user_id = registered.json()["id"]
                        await backend.rbac.create_role(Role(name="editor"))
                        await backend.rbac.create_permission(Permission(name="documents.create"))
                        await backend.rbac.assign_permission_to_role("editor", "documents.create")
                        await backend.rbac.assign_role_to_user(user_id, "editor")

                        login = await client.post(
                            "/auth/login",
                            json={"identifier": "clean@example.com", "password": "password123"},
                        )
                        assert login.status_code == 200, login.text
                        tokens = login.json()
                        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                        assert (await client.get("/me", headers=headers)).status_code == 200
                        assert (await client.post("/documents", headers=headers)).status_code == 200

                        rotated = await client.post(
                            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
                        )
                        assert rotated.status_code == 200, rotated.text
                        logout = await client.post(
                            "/auth/logout",
                            headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
                            json={"refresh_token": rotated.json()["refresh_token"]},
                        )
                        assert logout.status_code == 204
                        rejected = await client.post(
                            "/auth/refresh",
                            json={"refresh_token": rotated.json()["refresh_token"]},
                        )
                        assert rejected.status_code == 401
                finally:
                    await backend.close()

            asyncio.run(main())
            """
        ).strip()
        + "\n"
    )
    subprocess.run(["uv", "venv", str(tmp_path / "venv")], check=True, cwd=tmp_path)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            f"{PROJECT_ROOT}[sqlalchemy]",
            "httpx",
        ],
        check=True,
        cwd=tmp_path,
    )
    completed = subprocess.run(
        [str(python), str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "sqlalchemy.orm" not in script.read_text()
    assert "UserORM" not in script.read_text()
