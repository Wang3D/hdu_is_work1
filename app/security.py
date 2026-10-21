import functools
import html
import os
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar, cast

import bcrypt
import jwt
from flask import jsonify, request

F = TypeVar("F", bound=Callable[..., object])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


def issue_token(user_id: int, login: str) -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    now = datetime.now(timezone.utc)
    ttl = int(os.environ.get("TOKEN_TTL_SECONDS", "900"))
    return jwt.encode(
        {
            "sub": str(user_id),
            "login": login,
            "iss": os.environ.get("JWT_ISSUER", "hdu-work1"),
            "aud": os.environ.get("JWT_AUDIENCE", "hdu-work1-client"),
            "iat": now,
            "exp": now + timedelta(seconds=ttl),
        },
        secret,
        algorithm="HS256",
    )


def token_required(handler: F) -> F:
    @functools.wraps(handler)
    def wrapped(*args: object, **kwargs: object) -> object:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Bearer token required"), 401
        token = header[7:].strip()
        secret = os.environ.get("JWT_SECRET")
        try:
            if not secret:
                raise RuntimeError("JWT_SECRET is not configured")
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=os.environ.get("JWT_AUDIENCE", "hdu-work1-client"),
                issuer=os.environ.get("JWT_ISSUER", "hdu-work1"),
            )
            request.user_id = int(cast(str, claims["sub"]))
            request.user_login = cast(str, claims["login"])
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            return jsonify(error="Invalid or expired token"), 401
        return handler(*args, **kwargs)

    return cast(F, wrapped)


def safe_text(value: str) -> str:
    return html.escape(value, quote=True)
