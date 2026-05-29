"""FastAPI application entrypoint.

Run locally:
    cd backend
    uvicorn app.main:app --reload

API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_auth, routes_health, routes_trip
from app.config import get_settings
from app.db.database import init_db
from app.utils.logger import RequestIdMiddleware, configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting Local Travel Suggester (db=%s, llm_mock=%s)",
        settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
        settings.llm_mock,
    )
    init_db()
    logger.info("DB tables ready")
    yield
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Local Travel Suggester",
        version="2.0.0",
        description=(
            "AI-curated trip recommendations: weather-aware, intent-driven, "
            "with AWS Bedrock reasoning and a Foursquare → OpenStreetMap fallback chain."
        ),
        lifespan=_lifespan,
    )

    # CORS: allow the Vite dev server and any same-origin requests.
    # In production, replace "*" with the actual frontend domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    app.include_router(routes_auth.router)
    app.include_router(routes_trip.router)
    app.include_router(routes_health.router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"message": "Local Travel Suggester API", "docs": "/docs", "health": "/health"}

    @app.get("/api", tags=["meta"])
    async def api_root() -> dict[str, str]:
        return {
            "name": "local-travel-suggester",
            "version": "2.0.0",
            "docs": "/docs",
            "health": "/health/detailed",
        }

    return app


app = create_app()
