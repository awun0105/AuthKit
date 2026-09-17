"""AuthKit plus an ORM-independent documents module."""

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from authkit import AuthKit, AuthKitConfig, AuthUser
from authkit.adapters.memory import MemoryBackend

backend = MemoryBackend()
auth = AuthKit(
    AuthKitConfig(
        secret_key="replace-with-at-least-32-random-bytes",
        require_email_verification=False,
    ),
    backend=backend,
)

documents = APIRouter(prefix="/documents", tags=["documents"])


@documents.get(
    "/{document_id}",
    dependencies=[Depends(auth.require_permission("documents.read"))],
)
async def get_document(
    document_id: str,
    current_user=Depends(auth.current_user),
) -> dict:
    identity: AuthUser | None = await auth.gateway.get_user(current_user.id)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity disappeared")
    return {"id": document_id, "requested_by": identity.model_dump()}


app = FastAPI(title="AuthKit modular monolith example")
app.include_router(auth.router, prefix="/auth")
app.include_router(documents)
