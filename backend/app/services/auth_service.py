"""Authentication business logic.

Separated from routes so it can be tested without HTTP — just call the
functions with a DB session and get back a result or an exception.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import Token, UserCreate, UserLogin


def register_user(db: Session, data: UserCreate) -> Token:
    """Create a new user account. Raises 409 if the email is already registered."""
    existing = db.execute(
        select(User).where(User.email == data.email.lower())
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Also check username uniqueness
    username_taken = db.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()
    if username_taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    user = User(
        username=data.username,
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return Token(access_token=token)


def login_user(db: Session, data: UserLogin) -> Token:
    """Verify credentials and return a JWT. Raises 401 on failure.

    We return 401 for both "email not found" and "wrong password" — this
    prevents user enumeration attacks (an attacker can't tell which one failed).
    """
    user = db.execute(
        select(User).where(User.email == data.email.lower())
    ).scalar_one_or_none()

    invalid_creds = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(data.password, user.hashed_password):
        raise invalid_creds

    token = create_access_token(user.id)
    return Token(access_token=token)
