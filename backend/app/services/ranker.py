"""Rule-based place ranker.

Score = 0.20 × weather_fit
      + 0.45 × preference_match   ← dominant signal
      + 0.15 × popularity
      + 0.20 × proximity

Why rule-based first (not LLM-only):
  - Scoring 30 candidates with the LLM would cost 30 API calls = 30-90 seconds.
  - Rule-based scoring runs in milliseconds and is deterministic.
  - The LLM's job is curating the TOP 2N shortlist — one call, not N calls.
  - If the LLM fails, rule-based top-N is the fallback. We always have a result.
"""

from __future__ import annotations

from typing import Any, Optional

_OUTDOOR_KEYWORDS = {
    "park", "garden", "lake", "beach", "fort", "hill", "trek", "waterfall",
    "viewpoint", "scenic", "outdoor", "zoo", "safari", "monument", "memorial",
    "natural", "water", "peak",
}
_INDOOR_KEYWORDS = {
    "museum", "gallery", "aquarium", "planetarium", "mall", "cafe",
    "restaurant", "theatre", "cinema", "library", "temple", "mosque",
    "church", "shrine", "spa", "place of worship",
}

_PROMPT_BUCKETS: dict[str, set[str]] = {
    "peaceful": {"park", "garden", "lake", "temple", "monastery", "shrine", "viewpoint", "beach", "place of worship"},
    "calm":     {"park", "garden", "lake", "temple", "viewpoint", "place of worship"},
    "quiet":    {"park", "garden", "library", "place of worship", "temple"},
    "adventure": {"fort", "trek", "hill", "water_park", "waterpark", "adventure", "amusement", "zoo", "safari", "peak", "cliff"},
    "thrill":   {"theme park", "amusement", "fort", "peak", "water_park"},
    "food":     {"market", "cafe", "restaurant", "bakery", "street", "cuisine", "bar", "pub", "fast food", "food court", "ice cream", "biergarten", "biryani"},
    "history":  {"fort", "museum", "monument", "memorial", "heritage", "palace", "ruins", "historic", "archaeological"},
    "historic": {"fort", "museum", "monument", "memorial", "historic", "palace", "heritage"},
    "heritage": {"fort", "monument", "heritage", "historic", "palace"},
    "family":   {"park", "zoo", "aquarium", "museum", "planetarium", "amusement", "mall", "theme park"},
    "kids":     {"zoo", "aquarium", "park", "amusement", "theme park", "planetarium"},
    "shopping": {"mall", "market", "bazaar", "shop", "shopping"},
    "spiritual": {"temple", "mosque", "church", "shrine", "monastery", "place of worship"},
    "religious": {"temple", "mosque", "church", "shrine", "place of worship"},
    "nature":   {"park", "garden", "lake", "hill", "waterfall", "beach", "forest", "viewpoint", "natural", "water", "wood"},
    "view":     {"viewpoint", "hill", "fort", "peak", "tower"},
    "scenic":   {"viewpoint", "hill", "lake", "garden", "beach"},
    "art":      {"gallery", "artwork", "museum", "theatre"},
    "romantic": {"viewpoint", "garden", "lake", "beach", "park"},
    "nightlife": {"bar", "pub", "lounge", "nightclub", "rooftop", "club", "live music"},
}


def _weather_fit(place: dict[str, Any], weather: dict[str, Any]) -> float:
    text = " ".join(place.get("categories") or []).lower()
    is_outdoor = any(k in text for k in _OUTDOOR_KEYWORDS)
    is_indoor = any(k in text for k in _INDOOR_KEYWORDS)
    condition = (weather.get("condition") or "").lower()
    temp = weather.get("temp_c")

    if "rain" in condition or "storm" in condition or "snow" in condition:
        return 1.0 if is_indoor else (0.15 if is_outdoor else 0.6)
    if isinstance(temp, (int, float)) and temp >= 36:
        return 0.9 if is_indoor else (0.45 if is_outdoor else 0.65)
    if "clear" in condition or "sun" in condition or "cloud" in condition:
        return 1.0 if is_outdoor else (0.7 if is_indoor else 0.8)
    return 0.7


def _prompt_match(place: dict[str, Any], preference: Optional[str]) -> float:
    if not preference:
        return 0.5

    pref_lower = preference.lower()
    text = " ".join([
        str(place.get("name") or ""),
        str(place.get("description") or ""),
        " ".join(place.get("categories") or []),
    ]).lower()

    if not text.strip():
        return 0.2

    matched_buckets = 0
    bucket_hits = 0
    for bucket_key, keywords in _PROMPT_BUCKETS.items():
        if bucket_key in pref_lower:
            matched_buckets += 1
            if any(k in text for k in keywords):
                bucket_hits += 1

    if matched_buckets > 0:
        return 0.1 if bucket_hits == 0 else min(1.0, bucket_hits / matched_buckets)

    tokens = [t for t in pref_lower.split() if len(t) > 3]
    if not tokens:
        return 0.5
    matched = sum(1 for t in tokens if t in text)
    return 0.5 + min(0.4, 0.2 * matched) if matched > 0 else 0.25


def _proximity(distance_km: Optional[float], horizon_km: float = 25.0) -> float:
    if distance_km is None:
        return 0.6  # neutral when no locality provided
    if distance_km <= 0:
        return 1.0
    if distance_km >= horizon_km:
        return 0.0
    return 1.0 - (distance_km / horizon_km)


def _popularity(place: dict[str, Any]) -> float:
    pop = place.get("popularity")
    if isinstance(pop, (int, float)):
        return max(0.0, min(1.0, float(pop)))
    rating = place.get("rating")
    if isinstance(rating, (int, float)):
        return max(0.0, min(1.0, float(rating) / 10.0))
    return 0.4


def score_place(
    place: dict[str, Any],
    weather: dict[str, Any],
    preference: Optional[str],
) -> float:
    return round(
        0.20 * _weather_fit(place, weather)
        + 0.45 * _prompt_match(place, preference)
        + 0.15 * _popularity(place)
        + 0.20 * _proximity(place.get("_distance_km")),
        4,
    )


def rank_places(
    places: list[dict[str, Any]],
    weather: dict[str, Any],
    preference: Optional[str],
    max_results: int,
    *,
    max_per_category: int = 2,
) -> list[dict[str, Any]]:
    """Return top max_results places, scored and diversity-capped.

    Diversity rule: at most max_per_category places with the same primary
    category. Without this you'd get 5 museums in a row for "history" prompts.
    If diversity leaves us short, we top up from the remaining pool.
    """
    scored = []
    for p in places:
        if not (p.get("coords") or {}).get("lat"):
            continue
        enriched = dict(p)
        enriched["_score"] = score_place(p, weather, preference)
        scored.append(enriched)

    scored.sort(key=lambda row: row["_score"], reverse=True)

    picked: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    leftover: list[dict[str, Any]] = []

    for row in scored:
        cat = (row.get("categories") or ["uncategorised"])[0].strip().lower()
        if category_counts.get(cat, 0) < max_per_category:
            picked.append(row)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if len(picked) >= max_results:
                return picked
        else:
            leftover.append(row)

    for row in leftover:
        if len(picked) >= max_results:
            break
        picked.append(row)

    return picked
