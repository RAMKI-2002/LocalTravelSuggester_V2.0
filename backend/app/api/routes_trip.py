"""Trip suggestion and history endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import QueryHistory, User
from app.schemas.trip import TripRequest, TripResponse
from app.services.trip_service import suggest_trip

logger = logging.getLogger(__name__)
router = APIRouter(tags=["trip"])


@router.post("/suggest-trip", response_model=TripResponse)
async def suggest_trip_endpoint(
    req: TripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripResponse:
    """Recommend tourist places for a city based on weather + user intent.

    Requires authentication — the query is saved to the user's history.
    """
    logger.info(
        "suggest-trip: user=%d city=%r pref=%r locality=%r max=%s",
        current_user.id, req.city, req.preference, req.locality, req.max_results,
    )
    return await suggest_trip(db, req, user_id=current_user.id)


@router.get("/history")
def history(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the authenticated user's most recent trip queries.

    History is user-scoped — users cannot see each other's queries.
    """
    rows = db.execute(
        select(QueryHistory)
        .where(QueryHistory.user_id == current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(limit)
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for row in rows:
        payload = row.response or {}
        suggestions = payload.get("suggestions") or []
        meta = payload.get("meta") or {}
        items.append({
            "id": row.id,
            "city": row.city,
            "preference": row.preference,
            "locality": row.locality,
            "suggestion_count": len(suggestions),
            "top_suggestion": suggestions[0]["name"] if suggestions else None,
            "latency_ms": row.latency_ms,
            "degraded": meta.get("degraded") or [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return {"count": len(items), "items": items}
