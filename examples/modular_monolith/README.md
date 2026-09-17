# Modular-monolith example

The fake `documents` module imports only the public facade/DTO. It does not
import AuthKit's storage models or SQLAlchemy adapter internals.

```bash
uv run uvicorn examples.modular_monolith.main:app --reload
```
