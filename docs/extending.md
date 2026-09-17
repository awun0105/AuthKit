# Extending AuthKit

Implement core Protocol ports to add MongoDB, DynamoDB, Supabase, SQLModel, or a
corporate IAM adapter. Package adapter internals behind a backend composition
object and keep flows unaware of the storage technology.

Identity remains minimal. Store domain data in application-owned tables keyed
by AuthKit's string user ID. `extra_data` remains available for small identity
metadata, but it is not the recommended home for business aggregates.

Custom email/SMS transports, notification routing, templates, password
handlers, token blacklists, session stores, OAuth state stores, audit sinks, and
event sinks can be supplied explicitly to `AuthKit`.
