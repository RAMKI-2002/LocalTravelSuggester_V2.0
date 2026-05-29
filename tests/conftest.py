"""Shared test fixtures.

All tests use:
  - In-memory SQLite (no real DB needed)
  - LLM_MOCK=true (no AWS calls)
  - respx for mocking external HTTP calls
"""

from __future__ import annotations

import os
import sys

# Ensure the NEW backend/ is at the FRONT of sys.path.
# The workspace root (LocalTravelSuggester/) contains the OLD app/ package
# which must not shadow the new backend/app/. We insert backend/ at index 0
# and remove the workspace root if it is present.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
_WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Remove workspace root from path to prevent old app/ from shadowing backend/app/
while _WORKSPACE_ROOT in sys.path:
    sys.path.remove(_WORKSPACE_ROOT)

if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Set test environment BEFORE importing the app so Settings picks them up.
os.environ["DATABASE_URL"] = "sqlite:///./test_local_travel.db"
os.environ["LLM_MOCK"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["FOURSQUARE_ENABLED"] = "false"  # use Overpass in tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.database import Base, get_db
from app.main import create_app
from app.clients.llm_client import reset_llm_client


TEST_DATABASE_URL = "sqlite:///./test_local_travel.db"


@pytest.fixture(scope="session", autouse=True)
def _reset_settings_cache():
    """Clear lru_cache so test env vars take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_engine):
    """FastAPI TestClient with isolated SQLite DB and mocked LLM."""
    reset_llm_client()
    TestSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client) -> dict:
    """Register a test user and return the response JSON."""
    resp = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()


@pytest.fixture
def auth_headers(registered_user) -> dict:
    """Return Authorization headers for the registered test user."""
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
