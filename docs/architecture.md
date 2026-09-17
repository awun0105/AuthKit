# Architecture

Dependency direction is inward:

```text
FastAPI facade/router       CLI
          |                 |
          v                 v
flows + authorization + gateway + events
          |
          v
Pydantic models and Protocol ports
          ^
          |
memory / SQLAlchemy / Redis / consumer adapters
```

Core authentication, OAuth, MFA, sessions, notifications, audit, and RBAC
contracts do not import SQLAlchemy. `SQLAlchemyBackend` is a composition root
with narrow repositories (`users`, `sessions`, `rbac`, `audit`, token
revocation, refresh families, OAuth state). Custom adapters may implement the
same ports without inheriting from adapter classes.

`AuthKit` wires a backend to retained flows and builds instance-local FastAPI
dependencies and routers. There are no database connections or environment
mutations at import time.

Roles and permissions are loaded by the persistence adapter. Issued JWTs carry
role names and permission names in `roles` and `scopes`; a refresh obtains fresh
assignments. `current_user` always reloads identity and immediately rejects a
missing/disabled user. Login attaches the request User-Agent and hashed client
IP to the optional session record so logout can target that device.
