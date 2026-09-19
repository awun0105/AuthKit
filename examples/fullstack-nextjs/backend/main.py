"""FastAPI + AuthKit backend for the full-stack Next.js example."""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend
from authkit.authorization import Permission, Role
from authkit.events import AuthEvent

SECRET = "fullstack-example-secret-at-least-32-bytes"
backend = MemoryBackend()
auth = AuthKit(
    AuthKitConfig(
        secret_key=SECRET,
        access_token_ttl=int(os.environ.get("AUTHKIT_ACCESS_TOKEN_TTL", "900")),
        require_email_verification=False,
        enable_refresh_cookie=True,
        refresh_cookie_secure=False,
        refresh_cookie_samesite="lax",
    ),
    backend=backend,
)

app = FastAPI(title="AuthKit full-stack example")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3011"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/auth")


async def _seed() -> None:
    try:
        await backend.rbac.create_role(Role(name="member"))
    except ValueError:
        pass
    try:
        await backend.rbac.create_permission(Permission(name="documents.read"))
    except ValueError:
        pass
    try:
        await backend.rbac.assign_permission_to_role("member", "documents.read")
    except Exception:
        pass


async def _on_registered(event: AuthEvent) -> None:
    if event.user_id:
        await backend.rbac.assign_role_to_user(event.user_id, "member")


@app.on_event("startup")
async def startup() -> None:
    await _seed()
    auth.events.subscribe("UserRegistered", _on_registered)


@app.get("/documents")
async def list_documents(_user=Depends(auth.require_permission("documents.read"))):
    return [{"id": "welcome", "title": "Welcome document"}]


@app.post("/documents", status_code=201)
async def create_document(_user=Depends(auth.require_permission("documents.create"))):
    return {"id": "created", "title": "Created document"}
