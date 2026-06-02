"""Business logic for user-scoped place favorites."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import UserFavorite
from app.schemas.favorites import FavoriteItem, FavoritePlace

logger = logging.getLogger(__name__)


def _to_item(row: UserFavorite) -> FavoriteItem:
    return FavoriteItem(
        id=row.id,
        place_name=row.place_name,
        city=row.city,
        lat=row.lat,
        lng=row.lng,
        categories=row.categories or [],
        reasoning=row.reasoning,
        created_at=row.created_at,
    )


def create_favorite(
    db: Session,
    user_id: int,
    place: FavoritePlace,
    city: str,
) -> FavoriteItem:
    """Save a place for the user. Raises ValueError if already saved."""
    row = UserFavorite(
        user_id=user_id,
        place_name=place.name,
        city=city,
        lat=place.coords.lat,
        lng=place.coords.lng,
        categories=place.categories,
        reasoning=place.reasoning,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Place already saved") from None
    db.refresh(row)
    logger.info("favorite_created: user=%d place=%r", user_id, place.name)
    return _to_item(row)


def list_favorites(db: Session, user_id: int, limit: int) -> list[FavoriteItem]:
    rows = db.execute(
        select(UserFavorite)
        .where(UserFavorite.user_id == user_id)
        .order_by(UserFavorite.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [_to_item(row) for row in rows]


def delete_favorite(db: Session, user_id: int, favorite_id: int) -> bool:
    """Delete a favorite owned by user_id. Returns False if not found."""
    row = db.execute(
        select(UserFavorite).where(
            UserFavorite.id == favorite_id,
            UserFavorite.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    logger.info("favorite_deleted: user=%d id=%d", user_id, favorite_id)
    return True
