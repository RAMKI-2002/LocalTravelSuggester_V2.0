"""OpenStreetMap Overpass API client — free no-key fallback for tourist POIs."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.clients.exceptions import UpstreamError
from app.config import get_settings
from app.db import cache as cache_helpers

logger = logging.getLogger(__name__)

OVERPASS_MIRRORS: list[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_HTTP_TIMEOUT_S: float = 30.0
OVERPASS_PING_QUERY: str = "[out:json];out;"

TOURISM_TAGS = {"attraction", "museum", "viewpoint", "gallery", "theme_park", "zoo", "aquarium", "artwork", "monument"}
LEISURE_TAGS = {"park", "garden", "nature_reserve", "water_park"}
AMENITY_TAGS = {"place_of_worship", "marketplace", "restaurant", "cafe", "bar", "pub", "fast_food", "food_court", "ice_cream", "biergarten"}
NATURAL_TAGS = {"water", "beach", "hill", "peak", "wood", "cliff"}
SHOP_TAGS = {"mall", "department_store", "supermarket", "books", "gift", "jewelry", "art", "craft"}


def _build_query_around(lat: float, lng: float, radius_m: int, limit: int) -> str:
    tourism_regex = "|".join(sorted(TOURISM_TAGS))
    leisure_regex = "|".join(sorted(LEISURE_TAGS))
    amenity_regex = "|".join(sorted(AMENITY_TAGS))
    natural_regex = "|".join(sorted(NATURAL_TAGS))
    shop_regex = "|".join(sorted(SHOP_TAGS))
    around = f"around:{int(radius_m)},{lat},{lng}"
    return f"""[out:json][timeout:25];
(
  node["tourism"~"^({tourism_regex})$"]({around});
  way ["tourism"~"^({tourism_regex})$"]({around});
  node["historic"]({around});
  way ["historic"]({around});
  node["leisure"~"^({leisure_regex})$"]({around});
  way ["leisure"~"^({leisure_regex})$"]({around});
  node["amenity"~"^({amenity_regex})$"]({around});
  way ["amenity"~"^({amenity_regex})$"]({around});
  node["natural"~"^({natural_regex})$"]({around});
  way ["natural"~"^({natural_regex})$"]({around});
  node["shop"~"^({shop_regex})$"]({around});
  way ["shop"~"^({shop_regex})$"]({around});
);
out center tags {limit};""".strip()


def _build_query_by_name(city: str, limit: int) -> str:
    tourism_regex = "|".join(sorted(TOURISM_TAGS))
    leisure_regex = "|".join(sorted(LEISURE_TAGS))
    amenity_regex = "|".join(sorted(AMENITY_TAGS))
    natural_regex = "|".join(sorted(NATURAL_TAGS))
    shop_regex = "|".join(sorted(SHOP_TAGS))
    safe_city = city.replace('"', "")
    return f"""[out:json][timeout:25];
area["name"="{safe_city}"]["boundary"="administrative"]->.searchArea;
(
  node["tourism"~"^({tourism_regex})$"](area.searchArea);
  way ["tourism"~"^({tourism_regex})$"](area.searchArea);
  node["historic"](area.searchArea);
  way ["historic"](area.searchArea);
  node["leisure"~"^({leisure_regex})$"](area.searchArea);
  way ["leisure"~"^({leisure_regex})$"](area.searchArea);
  node["amenity"~"^({amenity_regex})$"](area.searchArea);
  way ["amenity"~"^({amenity_regex})$"](area.searchArea);
  node["natural"~"^({natural_regex})$"](area.searchArea);
  way ["natural"~"^({natural_regex})$"](area.searchArea);
  node["shop"~"^({shop_regex})$"](area.searchArea);
  way ["shop"~"^({shop_regex})$"](area.searchArea);
);
out center tags {limit};""".strip()


def _extract_categories(tags: dict[str, Any]) -> list[str]:
    cats: list[str] = []
    tourism = tags.get("tourism")
    historic = tags.get("historic")
    leisure = tags.get("leisure")
    amenity = tags.get("amenity")
    natural = tags.get("natural")
    religion = tags.get("religion")
    cuisine = tags.get("cuisine")
    shop = tags.get("shop")

    if tourism:
        cats.append(tourism.replace("_", " ").title())
    if historic:
        cats.append(f"Historic {historic.replace('_', ' ').title()}")
    if leisure:
        cats.append(leisure.replace("_", " ").title())
    if amenity == "place_of_worship":
        cats.append(f"{religion.title()} Temple" if religion else "Place of Worship")
    elif amenity == "marketplace":
        cats.append("Market")
    elif amenity in {"restaurant", "cafe", "bar", "pub", "fast_food", "food_court", "ice_cream", "biergarten"}:
        label = amenity.replace("_", " ").title()
        if cuisine and amenity in {"restaurant", "cafe", "fast_food", "food_court"}:
            cats.append(f"{cuisine.title()} {label}")
        else:
            cats.append(label)
    if natural:
        cats.append(natural.replace("_", " ").title())
    if shop:
        cats.append(shop.replace("_", " ").title())
        cats.append("Shopping")
    return cats


def _normalise(element: dict[str, Any]) -> Optional[dict[str, Any]]:
    tags = element.get("tags") or {}
    name = tags.get("name") or tags.get("name:en")
    if not name:
        return None

    if element.get("type") == "node":
        lat = element.get("lat")
        lng = element.get("lon")
    else:
        center = element.get("center") or {}
        lat = center.get("lat")
        lng = center.get("lon")

    if lat is None or lng is None:
        return None

    address_parts = [
        tags.get("addr:housenumber"), tags.get("addr:street"),
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"), tags.get("addr:city"),
    ]
    address = ", ".join(p for p in address_parts if p) or None

    return {
        "fsq_id": f"osm:{element.get('type')}/{element.get('id')}",
        "name": name,
        "description": tags.get("description") or tags.get("wikipedia") or "",
        "categories": _extract_categories(tags),
        "coords": {"lat": lat, "lng": lng},
        "address": address,
        "price_tier": None,
        "rating": None,
        "popularity": None,
        "website": tags.get("website") or tags.get("contact:website"),
    }


async def _post_overpass_one(url: str, query: str, timeout_s: float) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "local-trip-suggester/2.0 (+tourist-api-demo)",
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
            resp = await client.post(url, data={"data": query}, headers=headers)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"overpass transport error ({url}): {exc}") from exc

    if resp.status_code == 429:
        raise UpstreamError(f"overpass 429 ({url})")
    if resp.status_code >= 400:
        raise UpstreamError(f"overpass {resp.status_code} ({url}): {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise UpstreamError(f"overpass non-JSON ({url}): {resp.text[:200]}") from exc


async def _fetch_overpass(query: str, timeout_s: float) -> dict[str, Any]:
    last_exc: Optional[UpstreamError] = None
    for url in OVERPASS_MIRRORS:
        try:
            return await _post_overpass_one(url, query, timeout_s)
        except UpstreamError as exc:
            logger.warning("overpass mirror failed (%s): %s", url, exc)
            last_exc = exc
    raise last_exc or UpstreamError("overpass: all mirrors failed")


async def ping_overpass(timeout_s: float = 5.0) -> tuple[bool, Optional[str]]:
    """Health probe: True if at least one mirror responds."""
    last_err: Optional[str] = None
    for url in OVERPASS_MIRRORS:
        try:
            await _post_overpass_one(url, OVERPASS_PING_QUERY, timeout_s)
            return True, url
        except UpstreamError as exc:
            last_err = str(exc)
    return False, last_err


class OverpassClient:
    """Cache-through wrapper around the public Overpass API."""

    DEFAULT_RADIUS_M = 25_000

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    async def search_tourist_places(
        self,
        city: str,
        *,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = DEFAULT_RADIUS_M,
        limit: int = 80,
    ) -> tuple[list[dict[str, Any]], bool]:
        if lat is not None and lng is not None:
            cache_key = f"osmv2:{lat:.2f},{lng:.2f}:{radius_m}"
            query = _build_query_around(lat, lng, radius_m, limit)
        else:
            cache_key = f"osm-name:{city.lower()}"
            query = _build_query_by_name(city, limit)

        fresh = cache_helpers.get_fresh_places(self.db, cache_key, self.settings.place_cache_ttl_hours)
        if fresh is not None:
            return fresh, True

        try:
            raw = await _fetch_overpass(query, OVERPASS_HTTP_TIMEOUT_S)
        except UpstreamError:
            stale = cache_helpers.get_stale_places(self.db, cache_key)
            if stale is not None:
                logger.warning("Overpass failed, serving stale OSM cache")
                return stale, True
            raise

        elements = raw.get("elements") if isinstance(raw, dict) else []
        normalised = [p for el in (elements or []) if (p := _normalise(el)) is not None]
        normalised = normalised[:limit]

        try:
            cache_helpers.store_places(self.db, cache_key, normalised, self.settings.place_cache_ttl_hours)
        except Exception:
            logger.exception("failed to store overpass cache")
        return normalised, False
