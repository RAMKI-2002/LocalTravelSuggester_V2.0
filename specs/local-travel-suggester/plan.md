# Technical Plan — Local Travel Suggester

**Stage:** 2 — Technical Plan & Task Breakdown
**Date:** 2026-05-25
**Method:** Spec Kit `/plan` equivalent

---

## 1. Stack Decisions

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Python 3.11 + FastAPI | Required by assessment; async-native; excellent Pydantic v2 integration |
| Data validation | Pydantic v2 | Required; strict mode; fast serialisation |
| Auth | JWT via python-jose + passlib[bcrypt] | Stateless; FastAPI Depends pattern; standard approach |
| Database | SQLite (dev) / PostgreSQL (prod) | SQLAlchemy 2.0 abstracts the difference; SQLite makes tests fast without Docker |
| HTTP client | httpx (async) | Used by the existing codebase; works with respx for testing |
| LLM | AWS Bedrock (Nova Lite via Converse API) | Credentials already configured; model-agnostic API |
| Retries | tenacity | Already used; exponential backoff with jitter |
| Frontend | React (JS) + Tailwind CSS via Vite | Modern, widely adopted; fast build; no TypeScript overhead for a 3-page app |
| Map | react-leaflet + Leaflet | OSM tiles are free; consistent with existing implementation |
| Testing | pytest + pytest-asyncio + respx + pytest-cov | Standard Python test stack |

---

## 2. Architecture

### 2.1 System Overview

```
Browser (React + Tailwind)
   |
   | HTTP / REST (JSON)
   |
FastAPI Backend (uvicorn)
   ├── /auth        → routes_auth.py    → auth_service.py
   ├── /suggest-trip → routes_trip.py  → trip_service.py
   ├── /history     → routes_trip.py   → DB query
   └── /health      → routes_health.py → probes

trip_service.py orchestrates:
   ├── GeocodeClient  → Nominatim (OSM)
   ├── WeatherClient  → OpenWeatherMap
   ├── PlacesClient   → Foursquare Places API
   ├── OverpassClient → OSM Overpass (fallback)
   ├── LLMClient      → AWS Bedrock (Nova Lite)
   └── SQLAlchemy DB  → SQLite / PostgreSQL
```

### 2.2 Backend Layer Responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| API | `api/routes_auth.py`, `api/routes_trip.py`, `api/routes_health.py` | HTTP: parse request, call service, return response |
| Core | `core/security.py` | JWT creation/verification, password hashing, `get_current_user` dependency |
| Services | `services/auth_service.py`, `services/trip_service.py`, `services/ranker.py`, `services/intent_parser.py`, `services/budget.py`, `services/distance.py` | Business logic; no HTTP |
| Clients | `clients/*.py` | Upstream API adapters; handle retries, caching, errors |
| DB | `db/database.py`, `db/models.py`, `db/cache.py` | ORM, session factory, TTL cache helpers |
| Schemas | `schemas/auth.py`, `schemas/trip.py` | Pydantic request/response models |
| Config | `config.py` | Pydantic Settings; single source of truth for env vars |

### 2.3 Frontend Structure

```
frontend/src/
├── main.jsx               entry point, ReactDOM.render
├── App.jsx                router (BrowserRouter), auth guard
├── api.js                 all fetch() calls in one place
├── context/
│   └── AuthContext.jsx    JWT token in localStorage, user state
└── pages/
    ├── LoginPage.jsx      register + login tabs
    ├── DashboardPage.jsx  form + map + suggestions
    └── HistoryPage.jsx    user's past queries
```

**Why one `api.js` file?** All 6 API calls are in one place. When the backend URL changes, one file changes. No hunting across components.

**Why useContext over Redux?** Three pages, one shared value (the JWT token). Context is explainable in one sentence: "the token lives in Context so any component can read it without prop drilling." Redux would add 4 files and a pattern that takes 10 minutes to explain.

---

## 3. Data Model

### 3.1 `users` Table

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Auto-increment |
| `username` | String(50) | Unique, indexed |
| `email` | String(256) | Unique, indexed |
| `hashed_password` | String | bcrypt hash |
| `created_at` | DateTime | server_default=now() |

### 3.2 `query_history` Table (updated)

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | — |
| `user_id` | Integer FK | → `users.id`, nullable (for backward compat) |
| `city` | String(128) | Indexed |
| `preference` | Text | Nullable |
| `locality` | String(256) | Nullable |
| `response` | JSON | Full `TripResponse` snapshot |
| `latency_ms` | Integer | — |
| `created_at` | DateTime | server_default=now() |

### 3.3 `place_cache` Table (unchanged)

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | — |
| `city` | String(128) | Unique key for cache lookup |
| `payload` | JSON | Normalised place list |
| `fetched_at` | DateTime | — |
| `expires_at` | DateTime | Indexed for TTL check |

### 3.4 `weather_log` Table (unchanged)

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | — |
| `city` | String(128) | Indexed |
| `payload` | JSON | Normalised weather snapshot |
| `fetched_at` | DateTime | — |
| `expires_at` | DateTime | Indexed for TTL check |

---

## 4. API Contracts

### 4.1 Auth Endpoints

#### POST /auth/register
```json
Request:  { "username": "alice", "email": "alice@example.com", "password": "secret123" }
Response: { "access_token": "eyJ...", "token_type": "bearer" }
Errors:   409 if email already registered
```

#### POST /auth/login
```json
Request:  { "email": "alice@example.com", "password": "secret123" }
Response: { "access_token": "eyJ...", "token_type": "bearer" }
Errors:   401 if credentials invalid
```

#### GET /auth/me
```json
Headers:  Authorization: Bearer <token>
Response: { "id": 1, "username": "alice", "email": "alice@example.com", "created_at": "..." }
Errors:   401 if token missing/invalid
```

### 4.2 Trip Endpoints

#### POST /suggest-trip
```json
Headers:  Authorization: Bearer <token>
Request:  { "city": "Hyderabad", "preference": "peaceful places", "locality": "Gachibowli", "max_results": 5 }
Response: {
  "city": "Hyderabad",
  "weather": { "temp_c": 28.5, "condition": "Clear", ... },
  "user_location": { "lat": 17.44, "lng": 78.35 },
  "suggestions": [
    {
      "name": "Hussain Sagar Lake",
      "description": "...",
      "categories": ["lake", "park"],
      "reasoning": "Perfect for a peaceful evening given the clear skies at 28°C.",
      "coords": { "lat": 17.42, "lng": 78.47 },
      "distance_km": 12.3,
      "estimated_budget": { "currency": "INR", "entry": 0, "travel": 370 },
      "score": 0.82
    }
  ],
  "meta": { "elapsed_ms": 2840, "cache_hits": ["weather"], "degraded": [], "llm_curate_used": true }
}
```

#### GET /history?limit=10
```json
Headers:  Authorization: Bearer <token>
Response: [
  { "id": 42, "city": "Hyderabad", "preference": "peaceful places", "created_at": "..." }
]
```

### 4.3 Health Endpoints

#### GET /health
```json
Response: { "status": "ok" }
```

#### GET /health/detailed
```json
Response: {
  "status": "ok",
  "checks": {
    "database": { "status": "ok", "elapsed_ms": 2 },
    "openweather": { "status": "ok", "elapsed_ms": 180 },
    "foursquare": { "status": "disabled", "note": "no API key configured" },
    "overpass": { "status": "ok", "elapsed_ms": 310 },
    "llm": { "status": "ok", "note": "bedrock client ready" }
  }
}
```

---

## 5. Authentication Flow

```
Client                     Server
  |                           |
  |-- POST /auth/register --> |
  |                           | hash password (bcrypt)
  |                           | insert users row
  |                           | create JWT (24h expiry)
  |<-- { access_token } ----- |
  |                           |
  |-- POST /suggest-trip ---> |
  |   Authorization: Bearer   | decode JWT → user_id
  |                           | attach user_id to request context
  |                           | run pipeline, persist history
  |<-- TripResponse ----------|
```

**JWT Payload:**
```json
{ "sub": "1", "exp": 1748800000 }
```
`sub` is the user ID as a string. Standard JWT claim. No sensitive data in payload.

---

## 6. Trip Suggestion Pipeline (Sequence)

```
POST /suggest-trip
  │
  ├─[parallel]─ Geocode city          (Nominatim)
  ├─[parallel]─ Geocode locality      (Nominatim, if provided)
  └─[parallel]─ Extract intent        (rule-based → Bedrock if ambiguous)
  │
  ├─[parallel]─ Fetch weather         (OpenWeather → cache)
  └─[parallel]─ Fetch places          (Foursquare → Overpass fallback)
  │
  ├── Distance filter                 (>30 km from anchor → drop)
  ├── Score + rank (rule-based)       (weather + preference + popularity + proximity)
  ├── LLM curate                      (Bedrock picks best N from top 2N)
  ├── Budget estimation               (INR, per place)
  └── Persist to query_history (user_id attached)
  │
  └─► TripResponse
```

---

## 7. LLM Usage (Simplified from Original)

The original used `LLMProvider` abstract class → `BedrockLLMProvider` / `MockLLMProvider` → factory. This is replaced with a single `LLMClient` class:

```python
class LLMClient:
    def __init__(self):
        self._mock = get_settings().llm_mock
        if not self._mock:
            self._client = boto3.client("bedrock-runtime", ...)

    async def curate_places(self, ...) -> list | None: ...
    async def extract_intent(self, ...) -> dict | None: ...
    async def generate_place_reasoning(self, ...) -> str: ...
```

Mock behaviour is a branch inside each method, not a separate class. This eliminates the abstract base class, the factory function, and the two-file provider pattern.

**Decision:** Keep the same 3 LLM use cases (intent extraction, place curation, per-place reasoning). They provide distinct value and are independently testable.

---

## 8. Testing Plan

| Test File | What It Tests | Target Coverage |
|-----------|--------------|----------------|
| `tests/test_auth.py` | register, login, me, invalid creds, duplicate email | auth routes ~100% |
| `tests/test_trip.py` | suggest-trip happy path, no-auth, missing city, degraded weather | trip routes ~80% |
| `tests/test_health.py` | /health, /health/detailed structure | health routes ~90% |
| `tests/services/test_ranker.py` | score_place, rank_places, diversity cap | ranker.py ~95% |
| `tests/services/test_intent_parser.py` | rule hits, rule miss, LLM fallback, normalise | intent_parser.py ~90% |

**Test strategy:**
- All HTTP tests use FastAPI `TestClient` (synchronous, no running server needed)
- External API calls mocked with `respx` (no network in tests)
- LLM always mocked via `LLM_MOCK=true` in test environment
- Database uses in-memory SQLite (`DATABASE_URL=sqlite:///./test.db`)
- No Docker required for any test

---

## 9. Security Design

| Concern | Mitigation |
|---------|-----------|
| Password storage | bcrypt via passlib; never stored or logged in plain text |
| Token forgery | HS256 JWT signed with `SECRET_KEY` from env; not hardcoded |
| SQL injection | SQLAlchemy ORM parameterised queries |
| Input validation | Pydantic strict validation on all request bodies |
| API key exposure | All secrets in `.env`, never committed; `.env.example` has placeholder values |
| CORS | Configured to allow frontend origin in development; restrictive in production |
