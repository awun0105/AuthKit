"""Browser cookie mode and public frontend-support endpoints."""

from __future__ import annotations

import time

import httpx
import jwt
import pytest
from fastapi import FastAPI

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend
from authkit.routers.cookies import CSRF_HEADER, CSRF_HEADER_VALUE

SECRET = "authkit-browser-secret-at-least-32-bytes"


def _app(**config_kwargs) -> tuple[AuthKit, FastAPI]:
    backend = MemoryBackend()
    auth = AuthKit(
        AuthKitConfig(
            secret_key=SECRET,
            require_email_verification=False,
            **config_kwargs,
        ),
        backend=backend,
    )
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    return auth, app


@pytest.mark.asyncio
async def test_public_config_and_me_and_error_header() -> None:
    _auth, app = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        config = await client.get("/auth/config")
        assert config.status_code == 200
        body = config.json()
        assert body["allow_registration"] is True
        assert body["oauth_providers"] == []
        assert body["refresh_cookie"] is False

        await client.post(
            "/auth/register", json={"email": "me@example.com", "password": "password123"}
        )
        login = await client.post(
            "/auth/login", json={"identifier": "me@example.com", "password": "password123"}
        )
        token = login.json()["access_token"]
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "me@example.com"

        failed = await client.post(
            "/auth/login", json={"identifier": "me@example.com", "password": "wrong-password"}
        )
        assert failed.status_code == 401
        assert failed.headers["x-authkit-error"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_cookie_and_csrf() -> None:
    _auth, app = _app(enable_refresh_cookie=True, refresh_cookie_secure=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/auth/register", json={"email": "cookie@example.com", "password": "password123"}
        )
        login = await client.post(
            "/auth/login", json={"identifier": "cookie@example.com", "password": "password123"}
        )
        assert login.status_code == 200
        assert "authkit_refresh=" in login.headers.get("set-cookie", "")
        access = login.json()["access_token"]

        missing_csrf = await client.post("/auth/refresh", json={})
        assert missing_csrf.status_code == 403
        assert missing_csrf.headers["x-authkit-error"] == "CSRF_FAILED"

        rotated = await client.post(
            "/auth/refresh",
            json={},
            headers={CSRF_HEADER: CSRF_HEADER_VALUE},
        )
        assert rotated.status_code == 200, rotated.text
        assert rotated.json()["access_token"] != access

        missing_logout_csrf = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
        )
        assert missing_logout_csrf.status_code == 403
        assert missing_logout_csrf.headers["x-authkit-error"] == "CSRF_FAILED"

        logout = await client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {rotated.json()['access_token']}",
                CSRF_HEADER: CSRF_HEADER_VALUE,
            },
        )
        assert logout.status_code == 204
        assert "authkit_refresh=" in logout.headers.get("set-cookie", "")
        assert "authkit_authenticated=" in logout.headers.get("set-cookie", "")
        replay = await client.post(
            "/auth/refresh",
            json={},
            headers={CSRF_HEADER: CSRF_HEADER_VALUE},
        )
        assert replay.status_code in (400, 401)


@pytest.mark.asyncio
async def test_expired_access_token_exposes_refreshable_error_code() -> None:
    _auth, app = _app()
    expired = jwt.encode(
        {
            "sub": "missing-user",
            "jti": "expired-access",
            "type": "access",
            "roles": [],
            "scopes": [],
            "iat": int(time.time()) - 10,
            "exp": int(time.time()) - 1,
        },
        SECRET,
        algorithm="HS256",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
    assert response.status_code == 400  # preserved backend compatibility
    assert response.headers["x-authkit-error"] == "TOKEN_EXPIRED"
