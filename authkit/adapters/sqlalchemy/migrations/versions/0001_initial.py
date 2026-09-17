"""Create the isolated AuthKit identity schema.

Revision ID: 0001_authkit
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_authkit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authkit_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(512), nullable=True),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extra_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("mfa_pending_secret", sa.String(255), nullable=True),
        sa.Column("backup_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_verification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_otp_hash", sa.String(128), nullable=True),
        sa.Column("verification_otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_otp_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reset_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_token_hash", sa.String(128), nullable=True),
        sa.Column("reset_token_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_otp_hash", sa.String(128), nullable=True),
        sa.Column("reset_otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_otp_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_authkit_users_email"),
        sa.UniqueConstraint("username", name="uq_authkit_users_username"),
        sa.UniqueConstraint("phone_number", name="uq_authkit_users_phone"),
    )
    op.create_index("ix_authkit_users_email", "authkit_users", ["email"], unique=True)
    op.create_index("ix_authkit_users_username", "authkit_users", ["username"], unique=True)
    op.create_index("ix_authkit_users_phone_number", "authkit_users", ["phone_number"], unique=True)
    op.create_index("ix_authkit_users_is_active", "authkit_users", ["is_active"])
    op.create_index("ix_authkit_users_is_superuser", "authkit_users", ["is_superuser"])

    op.create_table(
        "authkit_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_authkit_roles_name"),
    )
    op.create_index("ix_authkit_roles_name", "authkit_roles", ["name"], unique=True)

    op.create_table(
        "authkit_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_authkit_permissions_name"),
    )
    op.create_index(
        "ix_authkit_permissions_name", "authkit_permissions", ["name"], unique=True
    )

    op.create_table(
        "authkit_user_roles",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("authkit_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("authkit_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "authkit_role_permissions",
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("authkit_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            sa.String(36),
            sa.ForeignKey("authkit_permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "authkit_oauth_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("authkit_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider", "provider_user_id", name="uq_authkit_oauth_provider_user"
        ),
        sa.UniqueConstraint("user_id", "provider", name="uq_authkit_user_oauth_provider"),
    )
    op.create_index("ix_authkit_oauth_accounts_user_id", "authkit_oauth_accounts", ["user_id"])
    op.create_index("ix_authkit_oauth_accounts_provider", "authkit_oauth_accounts", ["provider"])

    op.create_table(
        "authkit_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("authkit_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_hash", sa.String(128), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authkit_sessions_user_id", "authkit_sessions", ["user_id"])
    op.create_index("ix_authkit_sessions_expires_at", "authkit_sessions", ["expires_at"])

    op.create_table(
        "authkit_token_revocations",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_authkit_token_revocations_expires_at",
        "authkit_token_revocations",
        ["expires_at"],
    )

    op.create_table(
        "authkit_refresh_tokens",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("authkit_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authkit_refresh_family", "authkit_refresh_tokens", ["family_id"])
    op.create_index("ix_authkit_refresh_user", "authkit_refresh_tokens", ["user_id"])
    op.create_index("ix_authkit_refresh_expiry", "authkit_refresh_tokens", ["expires_at"])
    op.create_index("ix_authkit_refresh_revoked", "authkit_refresh_tokens", ["revoked_at"])
    op.create_index(
        "ix_authkit_refresh_family_revoked",
        "authkit_refresh_tokens",
        ["family_id", "revoked_at"],
    )

    op.create_table(
        "authkit_oauth_states",
        sa.Column("state", sa.String(128), primary_key=True),
        sa.Column("code_verifier", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authkit_oauth_states_expires_at", "authkit_oauth_states", ["expires_at"])

    op.create_table(
        "authkit_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("authkit_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("ip_hash", sa.String(128), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_authkit_audit_action", "authkit_audit_events", ["action"])
    op.create_index("ix_authkit_audit_user", "authkit_audit_events", ["user_id"])
    op.create_index("ix_authkit_audit_actor", "authkit_audit_events", ["actor_user_id"])
    op.create_index("ix_authkit_audit_created", "authkit_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("authkit_audit_events")
    op.drop_table("authkit_oauth_states")
    op.drop_table("authkit_refresh_tokens")
    op.drop_table("authkit_token_revocations")
    op.drop_table("authkit_sessions")
    op.drop_table("authkit_oauth_accounts")
    op.drop_table("authkit_role_permissions")
    op.drop_table("authkit_user_roles")
    op.drop_table("authkit_permissions")
    op.drop_table("authkit_roles")
    op.drop_table("authkit_users")
