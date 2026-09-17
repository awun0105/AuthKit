# Minimal example

```bash
uv run uvicorn examples.minimal.main:app --reload
```

Use `/docs` to register, login, authorize with the access token, call
`/protected`, refresh, and logout. The memory backend is for local development
and tests only; all state disappears on restart.
