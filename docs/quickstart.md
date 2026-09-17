# Quickstart

Install and run the memory example:

```bash
uv add authkit
uv run uvicorn examples.minimal.main:app --reload
```

The integration surface is intentionally small:

```python
backend = MemoryBackend()
auth = AuthKit(
    AuthKitConfig(
        secret_key="replace-with-at-least-32-random-bytes",
        require_email_verification=False,
    ),
    backend=backend,
)
app.include_router(auth.router, prefix="/auth")
```

Try the lifecycle through `/docs`:

1. `POST /auth/register` with email and password.
2. `POST /auth/login`; copy `access_token` into Swagger's Authorize dialog.
3. Call an endpoint using `Depends(auth.current_user)`.
4. `POST /auth/refresh` with the refresh token. The old token is consumed.
5. `POST /auth/logout` with the current bearer and refresh token.

For durable state, install `authkit[postgres]`, create a
`SQLAlchemyBackend`, and run `authkit db upgrade` before starting the app.
