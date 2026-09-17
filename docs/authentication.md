# Authentication

AuthKit preserves AuthWarden's register/login/logout, verification, password,
OAuth, and MFA flows. Access JWTs are short lived (15 minutes by default).
Refresh JWTs rotate by default; SQLAlchemy persists only JTI/family/expiry
metadata, never raw tokens. Replaying a consumed refresh token revokes the full
family.

Login uses a dummy password verification for unknown identities, applies
account lockout, checks active/verified status, validates optional TOTP, and
silently upgrades old password hashes. Forgot-password and resend-verification
responses are intentionally non-enumerating.

Password reset and password change revoke all persisted refresh records and
sessions when the backend supports those ports.
