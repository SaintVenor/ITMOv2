import argparse
import getpass
import sys

from app.db import SessionLocal, init_db
from app.models import ROLES
from app.services import auth
from app.services.errors import ServiceError


def create_user(args: argparse.Namespace) -> int:
    password = getpass.getpass("Пароль: ")
    if password != getpass.getpass("Повторите пароль: "):
        print("Пароли не совпадают", file=sys.stderr)
        return 1

    init_db()
    with SessionLocal() as db:
        try:
            user = auth.create_user(db, args.username, password, args.role, args.display_name)
        except ServiceError as exc:
            print(exc.message, file=sys.stderr)
            return 1
    print(f"Создан пользователь {user.username} ({user.role})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="создать пользователя")
    p.add_argument("--username", required=True)
    p.add_argument("--role", required=True, choices=ROLES)
    p.add_argument("--display-name", default=None)
    p.set_defaults(func=create_user)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
