"""User favorites endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.favorites import FavoriteCreate, FavoriteItem, FavoriteListResponse
from app.services import favorites_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["favorites"])


@router.post("/favorites", response_model=FavoriteItem, status_code=status.HTTP_201_CREATED)
def create_favorite_endpoint(
    body: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteItem:
    """Save a place from trip suggestions to the user's favorites."""
    logger.info("create_favorite: user=%d place=%r city=%r", current_user.id, body.place.name, body.city)
    try:
        return favorites_service.create_favorite(db, current_user.id, body.place, body.city)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/favorites", response_model=FavoriteListResponse)
def list_favorites_endpoint(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteListResponse:
    """Return the authenticated user's saved places."""
    items = favorites_service.list_favorites(db, current_user.id, limit)
    return FavoriteListResponse(count=len(items), items=items)


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite_endpoint(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a saved place. Returns 404 if missing or not owned by the user."""
    deleted = favorites_service.delete_favorite(db, current_user.id, favorite_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
