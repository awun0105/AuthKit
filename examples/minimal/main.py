"""Run with: uv run uvicorn examples.minimal.main:app --reload."""

from fastapi import Depends, FastAPI

from authkit import AuthKit, AuthKitConfig
from authkit.adapters.memory import MemoryBackend

backend = MemoryBackend()
auth = AuthKit(
    config=AuthKitConfig(
        secret_key="replace-with-at-least-32-random-bytes",
        require_email_verification=False,
    ),
    backend=backend,
)

app = FastAPI(title="AuthKit minimal example")
app.include_router(auth.router, prefix="/auth")


@app.get("/protected")
async def protected(user=Depends(auth.current_user)):
    return {"user_id": user.id, "email": user.email}
