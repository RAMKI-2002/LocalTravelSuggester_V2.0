"""Foursquare Places API client (post-2025 new platform).

Endpoint:  https://places-api.foursquare.com/places/search
Version:   X-Places-Api-Version: 2025-06-17

The circuit breaker from the original implementation is simplified to a
single class-level boolean flag. When the Foursquare free tier is exhausted,
the first 429 sets _billing_disabled=True and all subsequent requests skip
Foursquare entirely, going straight to Overpass.

Simplification decision: the original used a complex circuit-breaker class.
This version uses a 2-line flag check. Same behaviour, 1/3 the code.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.clients.exceptions import UpstreamError
from app.config import get_settings
from app.db import cache as cache_helpers
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FOURSQUARE_URL = "https://places-api.foursquare.com/places/search"
FOURSQUARE_API_VERSION = "2025-06-17"
DEFAULT_QUERY = "tourist attractions"

FIELDS = ",".join([
    "fsq_place_id", "name", "latitude", "longitude", "location",
    "categories", "rating", "description", "popularity",
    "tel", "website",
])


def _normalise(raw_place: dict[str, Any]) -> dict[str, Any]:
    categories = [c.get("name") for c in raw_place.get("categories") or [] if c]
    lat = raw_place.get("latitude")
    lng = raw_place.get("longitude")
    if isinstance(lat, dict):
        lat = lat.get("value")
    if isinstance(lng, dict):
        lng = lng.get("value")
    return {
        "fsq_id": raw_place.get("fsq_place_id"),
        "name": raw_place.get("name"),
        "description": raw_place.get("description") or "",
        "categories": [c for c in categories if c],
        "coords": {"lat": lat, "lng": lng},
        "address": (raw_place.get("location") or {}).get("formatted_address"),
        "rating": raw_place.get("rating"),
        "popularity": raw_place.get("popularity"),
        "website": raw_place.get("website"),
    }


class PlacesClient:
    """Cache-through wrapper around the Foursquare Places /search endpoint."""

    DEFAULT_RADIUS_M = 25_000

    # Class-level flag: set to True when the account runs out of API credits.
    # Future requests skip Foursquare and go straight to Overpass.
    _billing_disabled: bool = False

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    @classmethod
    def is_disabled(cls) -> bool:
        settings = get_settings()
        if not settings.foursquare_enabled:
            return True
        if not settings.foursquare_api_key:
            return True
        return cls._billing_disabled

    async def search_tourist_places(
        self,
        city: str,
        *,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = DEFAULT_RADIUS_M,
        limit: int = 30,
        query: str = DEFAULT_QUERY,
        cache_namespace: str = "tourist",
    ) -> tuple[list[dict[str, Any]], bool]:
        ns = "".join(ch for ch in (cache_namespace or "tourist").lower() if ch.isalnum())[:24] or "tourist"

        if lat is not None and lng is not None:
            cache_key = f"fsqv2:{lat:.2f},{lng:.2f}:{radius_m}:{ns}"
            params: dict[str, Any] = {
                "ll": f"{lat},{lng}", "radius": radius_m,
                "query": query, "limit": limit, "sort": "RELEVANCE", "fields": FIELDS,
            }
        else:
            cache_key = f"fsq-name:{city.lower()}:{ns}"
            params = {
                "near": city, "query": query, "limit": limit,
                "sort": "RELEVANCE", "fields": FIELDS,
            }

        fresh = cache_helpers.get_fresh_places(self.db, cache_key, self.settings.place_cache_ttl_hours)
        if fresh is not None:
            return fresh, True

        if PlacesClient.is_disabled():
            stale = cache_helpers.get_stale_places(self.db, cache_key)
            if stale is not None:
                return stale, True
            raise UpstreamError("Foursquare disabled (config or billing); no stale cache")

        headers = {
            "Authorization": f"Bearer {self.settings.foursquare_api_key}",
            "Accept": "application/json",
            "X-Places-Api-Version": FOURSQUARE_API_VERSION,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.settings.http_timeout_seconds)) as client:
                resp = await client.get(FOURSQUARE_URL, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Foursquare transport error: {exc}") from exc

        if resp.status_code == 429:
            msg = resp.text[:160]
            if "credit" in msg.lower() or "billing" in msg.lower():
                if not PlacesClient._billing_disabled:
                    PlacesClient._billing_disabled = True
                    logger.warning("Foursquare billing limit hit — switching to Overpass for this process")
            stale = cache_helpers.get_stale_places(self.db, cache_key)
            if stale is not None:
                return stale, True
            raise UpstreamError(f"Foursquare 429: {msg}")

        if resp.status_code >= 400:
            raise UpstreamError(f"Foursquare {resp.status_code}: {resp.text[:200]}")

        try:
            raw = resp.json()
        except ValueError as exc:
            raise UpstreamError(f"Foursquare non-JSON: {resp.text[:100]}") from exc

        items = raw.get("results") if isinstance(raw, dict) else []
        normalised = [_normalise(p) for p in items or []]
        normalised = [p for p in normalised if p["coords"]["lat"] is not None]

        try:
            cache_helpers.store_places(self.db, cache_key, normalised, self.settings.place_cache_ttl_hours)
        except Exception:
            logger.exception("failed to store places cache")
        return normalised, False
