"""AuthKit migration and secure bootstrap command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import shutil
from collections.abc import Sequence
from pathlib import Path


def _database_url(args: argparse.Namespace) -> str:
    value = args.database_url or os.environ.get("AUTHKIT_DATABASE_URL")
    if not value:
        raise SystemExit("database URL required: use --database-url or AUTHKIT_DATABASE_URL")
    return value


def _db_command(args: argparse.Namespace) -> None:
    from authkit import migrations

    database_url = _database_url(args)
    if args.db_action == "upgrade":
        migrations.upgrade(database_url, args.revision)
    elif args.db_action == "current":
        migrations.current(database_url)
    elif args.db_action == "history":
        migrations.history(database_url)


async def _create_admin_async(args: argparse.Namespace) -> None:
    from authkit.adapters.sqlalchemy import SQLAlchemyBackend
    from authkit.audit import AuditEvent
    from authkit.authentication.password import PasswordHandler
    from authkit.core.config import AuthKitConfig
    from authkit.models.user import UserInDB
    from authkit.utils import utcnow

    secret_key = args.secret_key or os.environ.get("AUTHKIT_SECRET_KEY")
    if not secret_key:
        raise SystemExit("secret key required: use --secret-key or AUTHKIT_SECRET_KEY")
    password = args.password or os.environ.get("AUTHKIT_ADMIN_PASSWORD")
    if not password and not args.promote_existing:
        password = getpass.getpass("Initial administrator password: ")

    config = AuthKitConfig(secret_key=secret_key, require_email_verification=False)
    password_handler = PasswordHandler(config)
    backend = SQLAlchemyBackend(_database_url(args))
    try:
        existing = await backend.users.get_by_email(args.email)
        if existing is not None:
            if not args.promote_existing:
                raise SystemExit(
                    "user already exists; pass --promote-existing to explicitly grant superuser status"
                )
            existing.is_superuser = True
            existing.is_active = True
            existing.updated_at = utcnow()
            user = await backend.users.update(existing)
        else:
            if not password:
                raise SystemExit("a password is required when creating a new administrator")
            password_handler.check_policy(password)
            now = utcnow()
            user = await backend.users.create(
                UserInDB(
                    email=args.email.strip().lower(),
                    hashed_password=password_handler.hash_password(password),
                    is_active=True,
                    is_verified=True,
                    is_superuser=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        await backend.audit.write(
            AuditEvent(action="admin.bootstrapped", user_id=user.id, actor_user_id=user.id)
        )
        print(f"AuthKit administrator ready: {user.email} ({user.id})")
    finally:
        await backend.close()


def _create_admin(args: argparse.Namespace) -> None:
    asyncio.run(_create_admin_async(args))


def _ui_init(args: argparse.Namespace) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = repo / "packages" / "cli" / "templates" / args.framework
    if not source.is_dir():
        raise SystemExit(
            "AuthKit UI templates are not in this Python install. "
            "From a JS project run: pnpm dlx @authkit/cli init --framework nextjs"
        )
    dest = Path(args.dir).resolve()
    created = skipped = 0
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        target = dest / path.relative_to(source)
        existed = target.exists()
        if existed and not args.force:
            print(f"skip\t{target.relative_to(dest)}")
            skipped += 1
            continue
        action = "overwrite" if existed else "create"
        if args.dry_run:
            print(f"{action}\t{target.relative_to(dest)}")
            created += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        print(f"{action}\t{target.relative_to(dest)}")
        created += 1
    print(f"AuthKit UI init: {created} written, {skipped} skipped")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="authkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    db = subparsers.add_parser("db", help="manage AuthKit's isolated migrations")
    db_subparsers = db.add_subparsers(dest="db_action", required=True)
    upgrade = db_subparsers.add_parser("upgrade")
    upgrade.add_argument("revision", nargs="?", default="head")
    for child in (upgrade, db_subparsers.add_parser("current"), db_subparsers.add_parser("history")):
        child.add_argument("--database-url")
        child.set_defaults(handler=_db_command)

    admin = subparsers.add_parser("create-admin", help="create the initial superuser explicitly")
    admin.add_argument("--database-url")
    admin.add_argument("--secret-key")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", help="prefer AUTHKIT_ADMIN_PASSWORD or the interactive prompt")
    admin.add_argument(
        "--promote-existing",
        action="store_true",
        help="explicitly promote an existing identity instead of refusing",
    )
    admin.set_defaults(handler=_create_admin)

    ui = subparsers.add_parser("ui", help="scaffold source-owned authentication UI")
    ui_sub = ui.add_subparsers(dest="ui_action", required=True)
    init = ui_sub.add_parser("init")
    init.add_argument("--framework", choices=("nextjs",), default="nextjs")
    init.add_argument("--dir", default=".")
    init.add_argument("--dry-run", action="store_true")
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=_ui_init)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    main()
