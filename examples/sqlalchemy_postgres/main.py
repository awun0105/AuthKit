"""PostgreSQL-backed AuthKit example."""

import os

from fastapi import Depends, FastAPI

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.sqlalchemy import SQLAlchemyBackend

database_url = os.environ.get(
    "AUTHKIT_DATABASE_URL",
    "postgresql+asyncpg://authkit:authkit@127.0.0.1:5432/authkit",
)
secret_key = os.environ["AUTHKIT_SECRET_KEY"]

backend = SQLAlchemyBackend(database_url=database_url)
auth = AuthKit(
    config=AuthKitConfig(
        secret_key=secret_key,
        require_email_verification=False,
        enable_admin_router=True,
    ),
    backend=backend,
)

app = FastAPI(title="AuthKit PostgreSQL example")
app.include_router(auth.router, prefix="/auth")


@app.get(
    "/documents",
    dependencies=[Depends(auth.require_permission("documents.read"))],
)
async def list_documents():
    return [{"id": "example-document"}]


@app.on_event("shutdown")
async def shutdown() -> None:
    await backend.close()
