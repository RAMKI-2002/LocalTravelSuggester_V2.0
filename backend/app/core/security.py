"""JWT authentication and password hashing.

Why JWT (not sessions):
  Stateless — the server stores nothing between requests. FastAPI's
  Depends() pattern makes auth reusable across any route in one line.
  Tradeoff: tokens can't be revoked before expiry without a blocklist.
  For this project's scope, 24-hour expiry is acceptable.

Why bcrypt (not SHA-256):
  bcrypt is intentionally slow (work factor tunable), making brute-force
  attacks computationally expensive. SHA-256 is fast by design — good for
  checksums, bad for password hashing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt as _bcrypt_lib
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db

# Swagger Authorize sends form-urlencoded; JSON login stays at POST /auth/login.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt. Truncates to 72 bytes (bcrypt's limit)."""
    return _bcrypt_lib.hashpw(plain[:72].encode(), _bcrypt_lib.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain[:72].encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.access_token_expire_hours
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> "User":  # type: ignore[name-defined]
    """FastAPI dependency: decode JWT and return the User row.

    Raises 401 if the token is missing, expired, or the user no longer exists.
    Import User lazily to avoid circular imports (models → database → security).
    """
    from app.db.models import User  # local import avoids circular dependency

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exc
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exc

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user
