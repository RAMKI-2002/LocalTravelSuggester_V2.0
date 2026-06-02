"""Pydantic request/response models for the trip-suggestion API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    city: str = Field(..., min_length=2, max_length=128, examples=["Hyderabad"])
    preference: Optional[str] = Field(
        default=None,
        max_length=500,
        examples=["peaceful places with good views"],
    )
    locality: Optional[str] = Field(
        default=None,
        max_length=256,
        examples=["Gachibowli"],
    )
    max_results: Optional[int] = Field(default=None, ge=1, le=10)


class Weather(BaseModel):
    temp_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    condition: Optional[str] = None
    description: Optional[str] = None
    humidity: Optional[int] = None
    wind_kph: Optional[float] = None


class Coords(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class PlaceSuggestion(BaseModel):
    name: str
    description: str = ""
    categories: list[str] = Field(default_factory=list)
    reasoning: str
    coords: Coords
    distance_km: Optional[float] = None
    score: float = 0.0
    website: Optional[str] = None
    address: Optional[str] = None


class TripIntentMeta(BaseModel):
    """Surfaces how the user's preference was parsed — useful for demo transparency."""

    category: str = "tourist"
    search_keywords: list[str] = Field(default_factory=list)
    mood: Optional[str] = None
    source: str = "default"


class TripMeta(BaseModel):
    elapsed_ms: int
    cache_hits: list[str] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)
    llm_provider: str
    llm_curate_used: bool = False
    intent: Optional[TripIntentMeta] = None


class TripResponse(BaseModel):
    city: str
    weather: Weather
    user_location: Optional[Coords] = None
    suggestions: list[PlaceSuggestion]
    meta: TripMeta
