# Migrations

Run AuthKit's packaged history independently:

```bash
authkit db upgrade --database-url "$AUTHKIT_DATABASE_URL"
authkit db current --database-url "$AUTHKIT_DATABASE_URL"
authkit db history --database-url "$AUTHKIT_DATABASE_URL"
```

The version table is `authkit_alembic_version`. Only `authkit_*` objects are
created. Re-running upgrade at head is safe.

Advanced consumers may import `authkit.adapters.sqlalchemy.metadata` into their
own Alembic autogeneration setup instead. They then own revision ordering and
must exclude AuthKit's packaged migration runner to avoid two histories owning
the same tables.
