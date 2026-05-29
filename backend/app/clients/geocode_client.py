"""OpenStreetMap Nominatim geocoding client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.clients.exceptions import NotFoundError, UpstreamError
from app.config import get_settings

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float
    display_name: str


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
    reraise=True,
)
async def _get_nominatim(params: dict, headers: dict, timeout: float) -> list:
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
    if resp.status_code == 404:
        raise NotFoundError("Nominatim 404")
    if resp.status_code >= 400:
        raise UpstreamError(f"Nominatim {resp.status_code}: {resp.text[:200]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise UpstreamError(f"Nominatim non-JSON: {resp.text[:200]}") from exc


class GeocodeClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def geocode(self, query: str) -> Optional[GeoPoint]:
        """Resolve a free-text query to lat/lng. Returns None on failure.

        Geocoding is advisory — a failure degrades to no-locality mode
        rather than breaking the whole request.
        """
        headers = {"User-Agent": self.settings.nominatim_user_agent}
        params = {"q": query, "format": "json", "limit": 1}

        try:
            data = await _get_nominatim(params, headers, self.settings.http_timeout_seconds)
        except NotFoundError:
            return None
        except UpstreamError as exc:
            logger.warning("Nominatim failed for '%s': %s", query, exc)
            return None

        if not data or not isinstance(data, list):
            return None

        top = data[0]
        try:
            return GeoPoint(
                lat=float(top["lat"]),
                lng=float(top["lon"]),
                display_name=top.get("display_name", query),
            )
        except (KeyError, TypeError, ValueError):
            return None
