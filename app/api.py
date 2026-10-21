import os
import re

from flask import Flask, jsonify, request

from .db import connection
from .security import issue_token, safe_text, token_required, verify_password

LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")


def create_app() -> Flask:
    app = Flask(__name__)

    @app.post("/auth/login")
    def login():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="JSON object required"), 400
        login_value = body.get("login")
        password = body.get("password")
        if (
            not isinstance(login_value, str)
            or not LOGIN_PATTERN.fullmatch(login_value)
            or not isinstance(password, str)
            or not 8 <= len(password) <= 128
        ):
            return jsonify(error="Invalid credentials"), 401
        with connection() as conn:
            user = conn.execute(
                "SELECT id, login, password_hash FROM users WHERE login = %s",
                (login_value,),
            ).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            return jsonify(error="Invalid credentials"), 401
        return jsonify(
            access_token=issue_token(user["id"], user["login"]),
            token_type="Bearer",
            expires_in=int(os.environ.get("TOKEN_TTL_SECONDS", "900")),
        )

    @app.get("/api/data")
    @token_required
    def get_data():
        with connection() as conn:
            rows = conn.execute(
                """
                SELECT id, content, created_at
                FROM data_items
                WHERE owner_id = %s
                ORDER BY id
                """,
                (request.user_id,),
            ).fetchall()
        return jsonify(
            data=[
                {
                    "id": row["id"],
                    "content": safe_text(row["content"]),
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]
        )

    @app.post("/api/data")
    @token_required
    def create_data():
        body = request.get_json(silent=True)
        content = body.get("content") if isinstance(body, dict) else None
        if not isinstance(content, str) or not 1 <= len(content) <= 500:
            return jsonify(error="content must be 1-500 characters"), 400
        with connection() as conn:
            row = conn.execute(
                """
                INSERT INTO data_items (owner_id, content)
                VALUES (%s, %s)
                RETURNING id, content, created_at
                """,
                (request.user_id, content),
            ).fetchone()
            conn.commit()
        return jsonify(
            id=row["id"],
            content=safe_text(row["content"]),
            created_at=row["created_at"].isoformat(),
        ), 201

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app
