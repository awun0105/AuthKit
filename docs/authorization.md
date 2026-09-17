# Authorization

Roles group permissions; users receive roles through a many-to-many relation.
Permission names must use `<resource>.<action>`, but AuthKit hard-codes no
resources, actions, or business roles.

```python
Depends(auth.require_role("reviewer"))
Depends(auth.require_permission("documents.approve"))
```

`permissions` and legacy `scopes` are the same authorization data: permissions
are emitted into the JWT `scopes` claim. Assignment changes take effect on the
next login/refresh; disabled users are still rejected immediately by
`current_user`.

AuthWarden also shipped an optional JWT role ladder
(`guest < user < moderator < admin < superadmin`) used by `has_min_role`.
That ladder is retained for compatibility. It is not the source of
database-backed roles, and AuthKit never treats those names as built-in
business roles. Official administration uses `is_superuser`, not the
`superadmin` ladder name.

The optional `/admin` router manages roles, permissions, role-permission links,
and user-role links. It is disabled by default and protected by fresh
`is_superuser` state, not by an assignable role name.
