"""Health and observability endpoints.

Two endpoints:
  GET /health          — liveness probe (cheap, no I/O)
  GET /health/detailed — readiness probe (concurrent per-dependency checks)

Design: probes run concurrently via asyncio.gather so one slow upstream
cannot block the whole health page. Each probe has an isolated 4s timeout.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.llm_client import get_llm_client
from app.clients.overpass_client import ping_overpass
from app.clients.places_client import PlacesClient
from app.config import get_settings
from app.db.database import get_db
from app.db.models import PlaceCache, QueryHistory, WeatherLog

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_PROBE_TIMEOUT = 4.0


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — process is up and responding."""
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_detailed(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Readiness probe with per-dependency status. Always returns 200."""
    settings = get_settings()
    started = time.perf_counter()

    results = await asyncio.gather(
        _check_db(db),
        _check_llm(),
        _probe("openweather", "GET", "https://api.openweathermap.org/data/2.5/weather",
               params={"q": "Hyderabad", "appid": settings.openweather_api_key or "", "units": "metric"},
               configured=bool(settings.openweather_api_key)),
        _foursquare_probe(),
        _overpass_probe(),
        _probe("nominatim", "GET", "https://nominatim.openstreetmap.org/search",
               params={"q": "Hyderabad", "format": "json", "limit": 1},
               headers={"User-Agent": settings.nominatim_user_agent},
               configured=True),
    )

    checks = {r["name"]: r for r in results}
    overall = "ok"
    for c in results:
        if c["status"] == "down" and c.get("configured", True):
            overall = "degraded"
            break

    llm = get_llm_client()
    return {
        "status": overall,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "checks": checks,
        "stats": _db_stats(db),
        "config": {
            "llm_mock": llm._mock,
            "bedrock_model": settings.bedrock_model_id,
            "db_kind": "postgres" if settings.is_postgres else "sqlite",
        },
    }


async def _check_db(db: Session) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        db.execute(select(1))
        return _ok("database", started, configured=True)
    except Exception as exc:
        return _down("database", started, str(exc), configured=True)


async def _check_llm() -> dict[str, Any]:
    started = time.perf_counter()
    llm = get_llm_client()
    if llm._mock:
        return _ok("llm", started, configured=False, note="mock-provider (no Bedrock call made)")
    return _ok("llm", started, configured=True, note=f"bedrock client ready ({llm._model_id})")


async def _foursquare_probe() -> dict[str, Any]:
    started = time.perf_counter()
    settings = get_settings()
    if not settings.foursquare_enabled:
        return _disabled("foursquare", started, "disabled by FOURSQUARE_ENABLED=false")
    if not settings.foursquare_api_key:
        return _disabled("foursquare", started, "no API key configured")
    if PlacesClient._billing_disabled:
        return _disabled("foursquare", started, "circuit breaker open (out of API credits)")
    return await _probe(
        "foursquare", "GET", "https://places-api.foursquare.com/places/search",
        params={"near": "Hyderabad", "query": "tourist attractions", "limit": 1},
        headers={"Authorization": f"Bearer {settings.foursquare_api_key}", "X-Places-Api-Version": "2025-06-17"},
        configured=True, ok_statuses=(200, 429),
    )


async def _overpass_probe() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        ok, info = await ping_overpass(timeout_s=_PROBE_TIMEOUT)
    except Exception as exc:
        return _down("overpass", started, str(exc)[:140], configured=True)
    if ok:
        return _ok("overpass", started, configured=True, note=f"reachable via {info}")
    return _down("overpass", started, f"all mirrors failed: {info or 'unknown'}", configured=True)


async def _probe(
    name: str, method: str, url: str, *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    configured: bool = True,
    ok_statuses: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    started = time.perf_counter()
    if not configured:
        return _down(name, started, "not configured", configured=False)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(_PROBE_TIMEOUT)) as c:
            resp = await c.request(method, url, params=params, headers=headers)
        if resp.status_code in ok_statuses:
            return _ok(name, started, configured=True, note=f"HTTP {resp.status_code}")
        return _down(name, started, f"HTTP {resp.status_code}", configured=True)
    except Exception as exc:
        return _down(name, started, str(exc)[:140], configured=configured)


def _db_stats(db: Session) -> dict[str, Any]:
    try:
        return {
            "history_rows": db.query(QueryHistory).count(),
            "place_cache_rows": db.query(PlaceCache).count(),
            "weather_log_rows": db.query(WeatherLog).count(),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _ok(name: str, started: float, *, configured: bool, note: str = "ok") -> dict[str, Any]:
    return {"name": name, "status": "ok", "configured": configured, "note": note,
            "elapsed_ms": int((time.perf_counter() - started) * 1000)}


def _down(name: str, started: float, error: str, *, configured: bool) -> dict[str, Any]:
    return {"name": name, "status": "down", "configured": configured, "note": error,
            "elapsed_ms": int((time.perf_counter() - started) * 1000)}


def _disabled(name: str, started: float, reason: str) -> dict[str, Any]:
    return {"name": name, "status": "disabled", "configured": False, "note": reason,
            "elapsed_ms": int((time.perf_counter() - started) * 1000)}
