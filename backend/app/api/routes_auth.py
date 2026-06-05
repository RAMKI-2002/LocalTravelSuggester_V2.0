"""Authentication endpoints: register, login, profile."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Register a new user account and return an access token."""
    logger.info("register: username=%r email=%r", data.username, data.email)
    return auth_service.register_user(db, data)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Verify credentials and return an access token (JSON body — used by frontend)."""
    logger.info("login: email=%r", data.email)
    return auth_service.login_user(db, data)


@router.post("/token", response_model=Token)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """OAuth2 form login for Swagger UI Authorize (username = email address)."""
    logger.info("token: email=%r", form_data.username)
    return auth_service.login_user(
        db,
        UserLogin(email=form_data.username, password=form_data.password),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
