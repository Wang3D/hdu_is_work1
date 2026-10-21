import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        yield conn


def initialize_schema() -> None:
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                login VARCHAR(64) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS data_items (
                id BIGSERIAL PRIMARY KEY,
                owner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 500),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        conn.commit()
