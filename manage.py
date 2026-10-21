import argparse
import os

from dotenv import load_dotenv

from app.db import connection, initialize_schema
from app.security import hash_password

load_dotenv()


def create_user(login: str, password: str) -> None:
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    with connection() as conn:
        conn.execute(
            "INSERT INTO users (login, password_hash) VALUES (%s, %s)",
            (login, hash_password(password)),
        )
        conn.commit()
    print(f"Created user {login!r}.")


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=True)
subparsers.add_parser("init-db")
user_parser = subparsers.add_parser("create-user")
user_parser.add_argument("--login", required=True)
user_parser.add_argument("--password")
args = parser.parse_args()

if args.command == "init-db":
    initialize_schema()
    print("Database schema is ready.")
elif args.command == "create-user":
    password = args.password or os.environ.get("WORK1_INITIAL_PASSWORD")
    if not password:
        import getpass
        password = getpass.getpass("Password: ")
    create_user(args.login, password)
