"""Create only the dedicated Work 1 role and database using an admin prompt."""
import getpass
import secrets
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    target = ROOT / ".env"
    if target.exists():
        raise SystemExit(".env already exists; refusing to overwrite it.")
    host = input("PostgreSQL host [127.0.0.1]: ").strip() or "127.0.0.1"
    port = input("PostgreSQL port [5432]: ").strip() or "5432"
    admin = input("Administrator [postgres]: ").strip() or "postgres"
    password = getpass.getpass("PostgreSQL administrator password (not saved): ")
    database, role = "hdu_is_work1", "work1_app"
    role_password = secrets.token_urlsafe(32)
    with psycopg.connect(
        host=host,
        port=port,
        user=admin,
        password=password,
        dbname="postgres",
        autocommit=True,
        connect_timeout=5,
    ) as conn:
        if conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            raise SystemExit(f"{database} already exists; refusing to alter it.")
        if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
            raise SystemExit(f"{role} already exists; refusing to alter it.")
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(role_password)
            )
        )
        try:
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(
                    sql.Identifier(database), sql.Identifier(role)
                )
            )
        except Exception:
            conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            raise
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
    url = f"postgresql://{role}:{quote(role_password, safe='')}@{host}:{port}/{database}"
    target.write_text(
        f"DATABASE_URL={url}\nJWT_SECRET={secrets.token_urlsafe(48)}\n"
        "JWT_ISSUER=hdu-work1\nJWT_AUDIENCE=hdu-work1-client\n"
        "TOKEN_TTL_SECONDS=900\nPORT=5000\n",
        encoding="utf-8",
    )
    print("Created hdu_is_work1 and work1_app. Secrets are saved to ignored .env.")


if __name__ == "__main__":
    main()
