"""Pydantic request/response models for the favorites API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.trip import PlaceSuggestion


class FavoritePlace(PlaceSuggestion):
    """Place payload for favorites — name must be non-empty."""

    name: str = Field(..., min_length=1, max_length=256)


class FavoriteCreate(BaseModel):
    place: FavoritePlace
    city: str = Field(..., min_length=2, max_length=128)


class FavoriteItem(BaseModel):
    id: int
    place_name: str
    city: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    categories: list[str] = Field(default_factory=list)
    reasoning: str = ""
    created_at: datetime


class FavoriteListResponse(BaseModel):
    count: int
    items: list[FavoriteItem]
