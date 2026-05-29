"""Coarse-grained budget estimator (INR).

These are indicative numbers only — they give the user a rough sense of cost
without pretending to be real pricing. The note field in the response makes
this explicit.
"""

from __future__ import annotations

from typing import Any, Optional

_PRICE_TIER_TO_INR = {1: 50, 2: 200, 3: 500, 4: 1200}
_PER_KM_INR = 24  # rough Indian metro cab/auto rate


def estimate_budget(
    place: dict[str, Any], distance_km: Optional[float]
) -> dict[str, Any]:
    tier = place.get("price_tier")
    entry = _PRICE_TIER_TO_INR.get(tier, 0) if isinstance(tier, int) else 0

    travel: Optional[int] = None if distance_km is None else int(round(distance_km * _PER_KM_INR))
    total: Optional[int]
    if travel is None:
        total = entry if entry else None
    else:
        total = entry + travel

    return {
        "currency": "INR",
        "entry": entry,
        "travel": travel,
        "total": total,
        "note": "Indicative. Entry from price tier; travel ~Rs.24/km cab proxy.",
    }
