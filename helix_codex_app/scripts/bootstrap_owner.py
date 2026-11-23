#!/usr/bin/env python3
"""
Create the first owner account for a fresh Helix Codex App installation.

A fresh app has zero accounts and no way to create one through the UI,
because the admin routes require an existing owner. This script seeds the
domain and the first owner so the operator can log in and invite the rest
of the team.

Usage:
    HELIX_OWNER_PASSWORD=your-password python helix_codex_app/scripts/bootstrap_owner.py \\
        --domain mycompany --username admin --password-env HELIX_OWNER_PASSWORD

The password may also come from --password-stdin or --password-file PATH;
argv --password still works but is deprecated (it leaks into shell history).
The domain's client_id defaults to the domain name; pass --client-id to set
it explicitly (the cockpit pack scopes its data by tenant and client).

Exit 0 = owner created. Exit 1 = bootstrap failed.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import uuid

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MIN_PASSWORD_LENGTH = 8


def bootstrap_owner(
    *,
    db_path: str,
    domain_name: str,
    username: str,
    password_secret: str,
    display_name: str | None = None,
    client_id: str | None = None,
) -> dict:
    """Create a domain and its first owner account, and record the event.

    Returns a dict with the domain name, tenant id, account id, username,
    and the governed node id so the caller can log the outcome.
    """
    from helix_codex_app import db
    from helix_codex_app.security.accounts import AccountRepository
    from helix_codex_app.security.passwords import hash_password

    conn = db.connect(db_path=db_path)
    db._init_schema(conn)
    try:
        repo = AccountRepository(conn)

        tenant_id = domain_name
        domain = repo.create_domain(domain_name, tenant_id, client_id=client_id)
        account = repo.create_account(
            domain.domain_id,
            username,
            password_hash=hash_password(password_secret),
            display_name=display_name or username,
            role_id="owner",
        )

        node_id = db.record_node(
            conn,
            tenant_id=tenant_id,
            client_id=domain.client_id,
            domain_id=domain.domain_id,
            correlation_id=f"bootstrap-{uuid.uuid4().hex}",
            classification="internal",
            nature="historical_event",
            created_by=account.account_id,
            provenance_source="helix_codex_app.bootstrap",
            provenance_data_mode="app_runtime",
            kind="admin",
            body={
                "action": "bootstrap_owner",
                "account_id": account.account_id,
                "username": account.username,
                "domain": domain_name,
            },
        )

        return {
            "domain": domain_name,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "account_id": account.account_id,
            "username": account.username,
            "role_id": "owner",
            "node_id": node_id,
        }
    finally:
        db.close(conn)


def _read_first_line(stream) -> str:
    line = stream.readline()
    return line.rstrip("\n").rstrip("\r")


def _resolve_password(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str | None:
    """Resolve the owner password from exactly one source.

    Order of preference is irrelevant because exactly one may be given.
    argv ``--password`` still works but warns, since it leaks into shell
    history and the process list.
    """
    sources = [
        bool(args.password),
        bool(args.password_env),
        bool(args.password_stdin),
        bool(args.password_file),
    ]
    chosen = sum(sources)
    if chosen != 1:
        parser.error(
            "provide exactly one of --password, --password-env, --password-stdin or --password-file"
        )

    resolved: str
    if args.password is not None:
        print(
            "warning: --password exposes the secret in shell history and the process list; "
            "use --password-env, --password-stdin or --password-file next time",
            file=sys.stderr,
        )
        resolved = args.password
    elif args.password_env is not None:
        value = os.environ.get(args.password_env, "")
        if not value:
            print(
                f"error: environment variable {args.password_env!r} is unset or empty",
                file=sys.stderr,
            )
            return None
        resolved = value
    elif args.password_stdin:
        resolved = _read_first_line(sys.stdin)
        if not resolved:
            print("error: stdin did not yield a password line", file=sys.stderr)
            return None
    else:
        path = pathlib.Path(args.password_file)
        try:
            resolved = _read_first_line(path.open("r", encoding="utf-8"))
        except OSError as exc:
            print(f"error: cannot read password file {path}: {exc}", file=sys.stderr)
            return None
        if not resolved:
            print(f"error: password file {path} is empty", file=sys.stderr)
            return None

    if len(resolved) < MIN_PASSWORD_LENGTH:
        print(f"error: password must be at least {MIN_PASSWORD_LENGTH} characters", file=sys.stderr)
        return None
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="helix_codex_app/app.db")
    parser.add_argument(
        "--domain",
        required=True,
        help="domain name, e.g. mycompany (used as tenant id and login suffix)",
    )
    parser.add_argument("--username", required=True, help="owner username")
    parser.add_argument("--display-name", default=None, help="owner display name")
    password_group = parser.add_argument_group(
        "password (exactly one is required; argv --password is deprecated)"
    )
    password_group.add_argument(
        "--password",
        default=None,
        help="DEPRECATED: visible in shell history and the process list. Prefer --password-env, --password-stdin or --password-file.",
    )
    password_group.add_argument(
        "--password-env",
        default=None,
        metavar="VAR",
        help="name of an environment variable holding the password",
    )
    password_group.add_argument(
        "--password-stdin",
        action="store_true",
        help="read the password from the first line of stdin",
    )
    password_group.add_argument(
        "--password-file",
        default=None,
        metavar="PATH",
        help="read the password from the first line of PATH (file mode is not checked; keep it 0600)",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help=(
            "client identifier for the domain (defaults to the domain name). "
            "The cockpit pack scopes its data by tenant and client, so a fresh "
            "install without one renders 'no pack data can be scoped'."
        ),
    )
    args = parser.parse_args(argv)

    owner_pw = _resolve_password(args, parser)
    if owner_pw is None:
        return 1

    client_id = args.client_id if args.client_id is not None else args.domain
    try:
        result = bootstrap_owner(
            db_path=args.db_path,
            domain_name=args.domain,
            username=args.username,
            password_secret=owner_pw,
            display_name=args.display_name,
            client_id=client_id,
        )
    except Exception as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"owner created: {result['username']}@{result['domain']} "
        f"(account={result['account_id']}, node={result['node_id']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
