import uuid
from typing import Any

import jwt
from datetime import UTC, datetime, timedelta
from pwdlib import PasswordHash
from app.core.config import get_settings

password_hash = PasswordHash().recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM
    )

def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=settings.JWT_ALGORITHM
        )
    except jwt.InvalidTokenError:
        return None
