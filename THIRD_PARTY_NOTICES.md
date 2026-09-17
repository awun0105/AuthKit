# Third-party notices

AuthKit is a fork and continuation of
[AuthWarden](https://github.com/timihack/authwarden), originally authored by
John Adeniran (`timihack`) and distributed under the MIT License. The original
authentication flows, FastAPI router composition, JWT/password/OAuth/MFA
implementation, notification abstractions, in-memory/Redis stores, and their
tests were retained and renamed as the starting point for AuthKit.

The following MIT-licensed repositories were studied as design references:

- [fastapi-auth-rbac](https://github.com/vishwap-bp/fastapi-auth-rbac) by
  `vishwap-bp`: relational RBAC, audit rows, refresh/session persistence, and
  Alembic organization. No source file or folder was copied into AuthKit.
- [fastapi-modular-monolith-starter-kit](https://github.com/arctikant/fastapi-modular-monolith-starter-kit)
  by `arctikant`: public DTO, gateway, event, and explicit-export patterns. No
  source file or folder was copied into AuthKit.

AuthKit's SQLAlchemy adapter, packaged migrations, RBAC contracts, audit/events
contracts, CLI, examples, and integration tests are AuthKit-native code written
against the retained AuthWarden protocols and behavior.
