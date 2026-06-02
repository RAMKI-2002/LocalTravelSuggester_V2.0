"""High-level orchestrator for POST /suggest-trip.

Pipeline:
  [1] Resolve     — parallel: geocode city, geocode locality, extract intent
  [2] Fan-out     — parallel: weather + places (Foursquare or Overpass)
  [3] Fallback    — Foursquare failure → Overpass
  [4] Filter      — drop candidates >30 km from anchor (Haversine)
  [5] Rank        — rule-based weighted score → shortlist of top 2N
  [6] Curate      — LLM picks best N from shortlist (ONE call); falls back to rule-based
  [7] Enrich      — per-place reasoning
  [8] Persist     — query_history (with user_id) → return TripResponse
"""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.clients.exceptions import UpstreamError
from app.clients.geocode_client import GeoPoint, GeocodeClient
from app.clients.llm_client import LLMClient, get_llm_client
from app.clients.overpass_client import OverpassClient
from app.clients.places_client import PlacesClient
from app.clients.weather_client import WeatherClient
from app.config import get_settings
from app.db.models import QueryHistory
from app.schemas.trip import (
    Coords, PlaceSuggestion, TripIntentMeta, TripMeta,
    TripRequest, TripResponse, Weather,
)
from app.services import ranker
from app.services.distance import haversine_km
from app.services.intent_parser import TripIntent, extract_intent

logger = logging.getLogger(__name__)

MAX_DISTANCE_KM = 30.0
SEARCH_RADIUS_M = 25_000


async def _geocode_safe(geocoder: GeocodeClient, query: str, label: str) -> Optional[GeoPoint]:
    try:
        return await geocoder.geocode(query)
    except UpstreamError as exc:
        logger.warning("geocode failed for %s (%r): %s", label, query, exc)
        return None


async def suggest_trip(db: Session, req: TripRequest, user_id: Optional[int] = None) -> TripResponse:
    settings = get_settings()
    max_results = req.max_results or settings.default_max_results

    start = perf_counter()
    cache_hits: list[str] = []
    degraded: list[str] = []

    weather_client = WeatherClient(db)
    places_client = PlacesClient(db)
    overpass_client = OverpassClient(db)
    geocoder = GeocodeClient()
    llm: LLMClient = get_llm_client()

    # [1] Parallel: geocode + intent extraction
    logger.info("[1] resolve: city=%r locality=%r preference=%r", req.city, req.locality, req.preference)
    city_geo_task = asyncio.create_task(_geocode_safe(geocoder, req.city, "city"))
    locality_geo_task = (
        asyncio.create_task(_geocode_safe(geocoder, f"{req.locality}, {req.city}", "locality"))
        if req.locality else None
    )
    intent_task = asyncio.create_task(extract_intent(req.preference, llm))

    city_point = await city_geo_task
    user_point: Optional[GeoPoint] = await locality_geo_task if locality_geo_task else None
    intent: TripIntent = await intent_task

    if req.locality and user_point is None:
        degraded.append("geocode_locality")
    if city_point is None:
        degraded.append("geocode_city")

    anchor_lat: Optional[float] = None
    anchor_lng: Optional[float] = None
    if user_point:
        anchor_lat, anchor_lng = user_point.lat, user_point.lng
    elif city_point:
        anchor_lat, anchor_lng = city_point.lat, city_point.lng

    # [2] Parallel: weather + places
    logger.info("[2] fan-out: weather + places (fsq_disabled=%s)", PlacesClient.is_disabled())
    weather_task = asyncio.create_task(weather_client.get(req.city))

    if PlacesClient.is_disabled():
        places_task = asyncio.create_task(
            overpass_client.search_tourist_places(req.city, lat=anchor_lat, lng=anchor_lng, radius_m=SEARCH_RADIUS_M)
        )
        degraded.append("places_primary_skipped")
    else:
        places_task = asyncio.create_task(
            places_client.search_tourist_places(
                req.city, lat=anchor_lat, lng=anchor_lng, radius_m=SEARCH_RADIUS_M,
                query=intent.query_string, cache_namespace=intent.category,
            )
        )

    try:
        weather_payload, weather_cached = await weather_task
    except UpstreamError as exc:
        logger.error("weather failed: %s", exc)
        weather_payload, weather_cached = {}, False
        degraded.append("weather")
    if weather_cached:
        cache_hits.append("weather")

    # [3] Places + fallback
    try:
        places_raw, places_cached = await places_task
        logger.info("[3] places: %d items (cached=%s)", len(places_raw), places_cached)
    except UpstreamError as exc:
        logger.warning("[3] primary places failed: %s", exc)
        if "places_primary_skipped" in degraded:
            places_raw, places_cached = [], False
            degraded.append("places")
        else:
            degraded.append("places_primary")
            try:
                places_raw, places_cached = await overpass_client.search_tourist_places(
                    req.city, lat=anchor_lat, lng=anchor_lng, radius_m=SEARCH_RADIUS_M,
                )
                degraded.append("places_fallback_overpass")
            except UpstreamError as fb_exc:
                logger.error("[3] overpass fallback failed: %s", fb_exc)
                places_raw, places_cached = [], False
                degraded.append("places")
    if places_cached:
        cache_hits.append("places")

    # [4] Distance filter
    if anchor_lat is not None and anchor_lng is not None:
        annotated: list[dict[str, Any]] = []
        for p in places_raw:
            coords = p.get("coords") or {}
            lat, lng = coords.get("lat"), coords.get("lng")
            if lat is None or lng is None:
                continue
            d = haversine_km(anchor_lat, anchor_lng, lat, lng)
            if d > MAX_DISTANCE_KM:
                continue
            p["_distance_km"] = round(d, 2)
            p["_distance_km_user"] = (
                round(haversine_km(user_point.lat, user_point.lng, lat, lng), 2)
                if user_point else None
            )
            annotated.append(p)
        logger.info("[4] distance filter: %d -> %d within %dkm", len(places_raw), len(annotated), int(MAX_DISTANCE_KM))
        places_raw = annotated
    else:
        for p in places_raw:
            p["_distance_km"] = None
            p["_distance_km_user"] = None

    # [5] Rank
    effective_pref = " ".join(s for s in [intent.category, intent.mood or "", req.preference or ""] if s).strip() or None
    shortlist_size = max(max_results * 2, 8)
    shortlist = ranker.rank_places(places_raw, weather_payload, effective_pref, shortlist_size)

    if not shortlist:
        elapsed_ms = int((perf_counter() - start) * 1000)
        response = _build_response(req, [], weather_payload, user_point, cache_hits, degraded + ["no_places"], elapsed_ms, llm, intent, False)
        _persist(db, req, response, elapsed_ms, user_id)
        return response

    # [6] LLM curate
    used_curate = False
    final_places: list[dict[str, Any]]
    try:
        curated = await llm.curate_places(weather_payload, req.preference, req.locality, shortlist, max_results)
    except Exception as exc:
        logger.warning("LLM curate raised, falling back: %s", exc)
        curated = None

    if curated:
        used_curate = True
        if len(curated) < max_results:
            chosen = {(p.get("name") or "").lower() for p in curated}
            for p in shortlist:
                if (p.get("name") or "").lower() not in chosen:
                    curated.append(p)
                if len(curated) >= max_results:
                    break
        final_places = curated[:max_results]
    else:
        if shortlist and not llm._mock:
            degraded.append("llm_curate")
        final_places = ranker.rank_places(places_raw, weather_payload, effective_pref, max_results)

    # [7] Enrich: per-place reasoning
    needs_reasoning = [p for p in final_places if "_reasoning" not in p]
    if needs_reasoning:
        async def _reason(place: dict[str, Any]) -> None:
            try:
                place["_reasoning"] = await llm.generate_place_reasoning(weather_payload, req.preference, place)
            except Exception as exc:
                logger.warning("LLM reasoning failed for %s: %s", place.get("name"), exc)
                degraded.append("llm")
                cond = (weather_payload.get("condition") or "current").lower()
                place["_reasoning"] = f"{place.get('name')} is recommended given the {cond} weather."

        await asyncio.gather(*(_reason(p) for p in needs_reasoning))

    elapsed_ms = int((perf_counter() - start) * 1000)
    response = _build_response(req, final_places, weather_payload, user_point, cache_hits, sorted(set(degraded)), elapsed_ms, llm, intent, used_curate)
    _persist(db, req, response, elapsed_ms, user_id)
    logger.info("[8] done: %d suggestions in %dms", len(response.suggestions), elapsed_ms)
    return response


def _build_response(
    req: TripRequest,
    places: list[dict[str, Any]],
    weather: dict[str, Any],
    user_point: Optional[GeoPoint],
    cache_hits: list[str],
    degraded: list[str],
    elapsed_ms: int,
    llm: LLMClient,
    intent: TripIntent,
    used_curate: bool,
) -> TripResponse:
    suggestions = [
        PlaceSuggestion(
            name=p.get("name") or "Unknown",
            description=p.get("description") or "",
            categories=p.get("categories") or [],
            reasoning=p.get("_reasoning") or "",
            coords=Coords(lat=(p.get("coords") or {}).get("lat"), lng=(p.get("coords") or {}).get("lng")),
            distance_km=p.get("_distance_km_user"),
            score=p.get("_score", 0.0),
            website=p.get("website"),
            address=p.get("address"),
        )
        for p in places
    ]
    return TripResponse(
        city=req.city,
        weather=Weather(
            temp_c=weather.get("temp_c"),
            feels_like_c=weather.get("feels_like_c"),
            condition=weather.get("condition"),
            description=weather.get("description"),
            humidity=weather.get("humidity"),
            wind_kph=weather.get("wind_kph"),
        ),
        user_location=Coords(lat=user_point.lat, lng=user_point.lng) if user_point else None,
        suggestions=suggestions,
        meta=TripMeta(
            elapsed_ms=elapsed_ms,
            cache_hits=cache_hits,
            degraded=degraded,
            llm_provider="MockLLMClient" if llm._mock else "BedrockLLMClient",
            llm_curate_used=used_curate,
            intent=TripIntentMeta(
                category=intent.category,
                search_keywords=intent.search_keywords,
                mood=intent.mood,
                source=intent.source,
            ),
        ),
    )


def _persist(db: Session, req: TripRequest, response: TripResponse, latency_ms: int, user_id: Optional[int]) -> None:
    try:
        entry = QueryHistory(
            user_id=user_id,
            city=req.city,
            preference=req.preference,
            locality=req.locality,
            response=response.model_dump(),
            latency_ms=latency_ms,
        )
        db.add(entry)
        db.commit()
    except Exception:
        logger.exception("failed to persist query history")
        db.rollback()
