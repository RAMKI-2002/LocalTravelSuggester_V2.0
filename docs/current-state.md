# Stage 0 — Existing Project Audit

**Date:** 2026-05-25
**Auditor:** Senior AI Application Engineer
**Project:** LocalTravelSuggester (pre-rebuild baseline)

---

## 1. Architecture Overview

The project is a single Python monolith served by FastAPI. The frontend is a collection of static HTML/CSS/JS files mounted directly by the server. There is no separate build pipeline or frontend framework.

```
FastAPI App (uvicorn)
 ├── API Layer         (app/api/)
 ├── Service Layer     (app/services/)
 ├── Client Layer      (app/clients/)
 ├── Database Layer    (app/db/)
 ├── Schemas           (app/schemas/)
 ├── Utils             (app/utils/)
 └── Static UI         (app/static/)   ← Vanilla JS, no framework
```

The core flow for a trip suggestion request:

```
POST /suggest-trip
 → [1] Geocode city + locality + Extract intent  (parallel)
 → [2] Fetch weather + places                   (parallel)
 → [3] Overpass fallback if Foursquare fails
 → [4] Distance filter (Haversine, >30 km dropped)
 → [5] Rule-based rank → LLM curate (Bedrock)
 → [6] Budget estimation + per-place reasoning
 → [7] Persist to DB → return TripResponse
```

---

## 2. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend framework | FastAPI | ≥0.115 |
| Data validation | Pydantic v2 | ≥2.10 |
| HTTP client | httpx | ≥0.27 |
| Database ORM | SQLAlchemy 2.0 | ≥2.0.41 |
| Database (dev) | SQLite | built-in |
| Database (prod) | PostgreSQL (Neon) | via psycopg3 |
| LLM provider | AWS Bedrock (Nova Lite) | via boto3 |
| Places data | Foursquare Places API (2025) | REST |
| Places fallback | OSM Overpass API | REST |
| Weather | OpenWeatherMap | REST |
| Geocoding | Nominatim (OSM) | REST |
| Retries | tenacity | ≥9.0 |
| Frontend | Vanilla JS + Leaflet | CDN |
| Styling | Custom CSS | none |

---

## 3. File Inventory (~35 files)

```
LocalTravelSuggester/
├── .env.example
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── api/
    │   ├── __init__.py
    │   ├── routes_health.py
    │   └── routes_trip.py
    ├── clients/
    │   ├── __init__.py
    │   ├── geocode_client.py
    │   ├── http_base.py          ← shared httpx client (to be removed)
    │   ├── llm_client.py         ← abstract class hierarchy (to be simplified)
    │   ├── overpass_client.py
    │   ├── places_client.py
    │   └── weather_client.py
    ├── db/
    │   ├── __init__.py
    │   ├── cache.py
    │   ├── database.py
    │   └── models.py
    ├── schemas/
    │   ├── __init__.py
    │   └── trip.py
    ├── services/
    │   ├── __init__.py
    │   ├── budget.py
    │   ├── distance.py
    │   ├── intent_parser.py
    │   ├── ranker.py
    │   └── trip_service.py
    ├── static/
    │   ├── app.js
    │   ├── how-it-works.css
    │   ├── how-it-works.html     ← architecture doc embedded in UI (to be moved)
    │   ├── index.html
    │   └── styles.css
    └── utils/
        ├── __init__.py
        ├── log_buffer.py         ← in-memory ring buffer (to be removed)
        └── logger.py
```

---

## 4. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Redirect to `/ui` |
| GET | `/ui` | Dashboard (index.html) |
| GET | `/how-it-works` | Architecture doc page |
| GET | `/static/*` | JS/CSS |
| GET | `/api` | Meta JSON |
| GET | `/health` | Liveness probe |
| GET | `/health/detailed` | Readiness + per-dependency checks |
| GET | `/logs` | In-memory log ring buffer |
| POST | `/suggest-trip` | Main recommendation pipeline |
| GET | `/history` | Last N query summaries |

---

## 5. Strengths (What Works Well)

### 5.1 Clean Service Layer Separation
The `services/` layer is well-designed: `trip_service.py` orchestrates all work, `ranker.py` is a pure function, `intent_parser.py` is independently testable. This layering survives the migration.

### 5.2 Resilience Patterns
- Foursquare → Overpass fallback chain
- Stale cache reads when upstream is down
- Per-dependency health checks with isolated timeouts
- Graceful degradation tags in `meta.degraded`

### 5.3 Intent-Driven Place Fetching
The intent parser (rule-based + LLM escalation) feeds different keywords to Foursquare for different prompts. This is the core insight that makes results non-generic.

### 5.4 Weighted Ranker
The scoring function `0.20*weather + 0.45*preference + 0.15*popularity + 0.20*proximity` with a diversity cap is explainable and tunable.

### 5.5 Pydantic v2 + FastAPI Type Safety
Strict input validation with clear error messages. `TripRequest`, `TripResponse` schemas are well-structured and production-ready.

---

## 6. Problems (Why Rebuild)

### 6.1 No User Authentication System (CRITICAL)
The requirements mandate "a user system." The existing project has zero authentication — no login, no register, no session ownership of history. This is a blocking gap.

### 6.2 Zero Tests (CRITICAL)
`pytest`, `pytest-asyncio`, and `respx` appear in `requirements.txt` but no test files exist anywhere. Backend coverage is 0%. Requirements mandate ≥70%.

### 6.3 No README
No root `README.md`. The project cannot be evaluated from GitHub without knowing how to run it.

### 6.4 No Required Artifact Structure
None of the required artifacts exist:
- No `specs/`
- No `docs/architecture.md`
- No `docs/performance.md`
- No `docs/security.md`
- No `docs/code-review.md`
- No `docs/retrospective.md`
- No `.cursor/rules/`
- No `AGENTS.md`
- No `openspec/changes/`

### 6.5 Frontend: Vanilla JS, No Framework
Requirements recommend React + Tailwind. The existing Vanilla JS works but does not support standard component-based practices and is harder to extend.

### 6.6 Over-Engineered Abstractions
- `LLMProvider` abstract class → `BedrockLLMProvider` → `MockLLMProvider` → factory `get_llm_provider()` is 4 layers for what is effectively one provider with a mock flag.
- `http_base.py` shared `httpx.AsyncClient` couples all clients together for marginal benefit.
- `log_buffer.py` in-memory ring buffer exposes a `/logs` endpoint that adds operational complexity for a demo.

### 6.7 Architecture Documentation Buried in UI
`how-it-works.html` is a static page served by the app itself. Architecture documentation should live in `docs/`, not in the deployed UI.

### 6.8 No CI/CD
No `.github/workflows/`, no Dockerfile, no docker-compose. The project cannot be verified in a fresh environment.

---

## 7. Technical Debt Summary

| Item | Severity | Migration Action |
|------|----------|-----------------|
| No tests | Critical | Write all tests first (TDD) in Stage 4 |
| No user auth | Critical | Add JWT auth in Stage 4 |
| No README | High | Write in final stage |
| Vanilla JS frontend | High | Rewrite in React + Tailwind (Stage 4) |
| LLM abstraction layers | Medium | Flatten to single `LLMClient` class |
| `http_base.py` shared client | Medium | Inline into each client |
| `log_buffer.py` ring buffer | Low | Remove; use structured logs only |
| Docs in UI | Low | Migrate to `docs/` |

---

## 8. Reuse Candidates

The following modules are well-written and will be moved (not rewritten) into `backend/app/`:

| Module | Reuse Decision |
|--------|---------------|
| `app/services/ranker.py` | Reuse — pure function, no deps, easily testable |
| `app/services/intent_parser.py` | Reuse — well-structured, LLM-fallback pattern is correct |
| `app/services/budget.py` | Reuse — simple INR estimation |
| `app/services/distance.py` | Reuse — pure Haversine math |
| `app/clients/weather_client.py` | Reuse (minor refactor to inline httpx) |
| `app/clients/places_client.py` | Reuse (simplify circuit breaker) |
| `app/clients/overpass_client.py` | Reuse |
| `app/clients/geocode_client.py` | Reuse |
| `app/db/database.py` | Reuse |
| `app/db/cache.py` | Reuse |
| `app/schemas/trip.py` | Reuse |
| `app/config.py` | Reuse (add auth secrets) |
| `app/utils/logger.py` | Reuse |

---

## 9. Migration Strategy

1. **Do not delete the existing code** — keep it as reference until the rebuild passes tests.
2. Create the full new folder structure (`backend/`, `frontend/`, `tests/`, `docs/`, `specs/`, `openspec/`).
3. Move reusable modules into `backend/app/` with minimal changes.
4. Rewrite LLM client (flatten), remove `http_base.py` and `log_buffer.py`.
5. Add User model + JWT auth system.
6. Write tests first for every new module.
7. Build React + Tailwind frontend separately in `frontend/`.
8. Remove the old `app/` folder once tests pass.

---

## 10. Baseline Metrics

| Metric | Value |
|--------|-------|
| Total Python files | ~28 |
| Test files | 0 |
| Backend test coverage | 0% |
| Frontend framework | None (Vanilla JS) |
| API endpoints | 10 |
| External integrations | 6 (Weather, Foursquare, Overpass, Nominatim, Bedrock, DB) |
| Docker / CI | None |
| README | Missing |
| Required stage artifacts | 0/6 stages complete |
