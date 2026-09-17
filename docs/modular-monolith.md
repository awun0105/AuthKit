# Modular-monolith integration

Business modules import the public `AuthUser` DTO and use
`auth.gateway.get_user(id)`. They never import `UserORM` or repository classes.
FastAPI handlers may depend on `auth.current_user`, `auth.require_role`, and
`auth.require_permission`.

`InProcessEventBus` supports async subscribers for meaningful lifecycle events
such as `UserRegistered`, `UserVerified`, `PasswordChanged`, `RoleAssigned`,
and `RoleRemoved`. It is intentionally not a durable broker.
