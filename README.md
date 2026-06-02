# Local Travel Suggester

AI-powered trip recommendations: weather-aware, intent-driven, with AWS Bedrock reasoning and a Foursquare → OpenStreetMap fallback chain.

Built as a complete, production-ready full-stack application following a structured 6-stage engineering process.

---

## What It Does

1. You enter a city and a travel preference ("I want something outdoors and budget-friendly")
2. The app fetches real-time weather for that city
3. It queries Foursquare (or OpenStreetMap if Foursquare is unavailable) for places
4. It parses your intent using rule-based matching + optional AWS Bedrock LLM
5. It ranks places by weather fit, preference match, and distance
6. AWS Bedrock generates a personalized reasoning for each suggestion
7. Results are shown on an interactive map (Leaflet) with suggestion cards
8. Every query is saved to your trip history (authentication required)

---

## Architecture Overview

```
frontend/  (React + Vite + Tailwind + react-leaflet)
    ↕  HTTP (via Vite proxy in dev)
backend/   (FastAPI + SQLAlchemy + Pydantic)
    ├── /auth        — register, login, profile (JWT)
    ├── /suggest-trip — full AI pipeline (auth required)
    ├── /history     — user's past queries (auth required)
    └── /health      — liveness + dependency readiness

External:
    OpenWeatherMap → weather
    Foursquare     → places (primary)
    Overpass/OSM   → places (fallback)
    Nominatim      → geocoding
    AWS Bedrock    → LLM reasoning (or mock in dev)
```

For the full architectural decision record, see [`docs/architecture.md`](docs/architecture.md).

---

## Project Structure

```
LocalTravelSuggester/
├── README.md
├── AGENTS.md              # AI collaboration roles and conventions
├── pytest.ini             # Pytest config (pythonpath = backend)
├── .cursor/
│   ├── rules/             # Cursor coding rules (project, fastapi, testing)
│   └── skills/            # Custom Cursor skills (test-writer)
├── specs/                 # Requirements spec, technical plan, task breakdown
├── openspec/changes/      # Change management records (CHG-001, CHG-002)
├── docs/
│   ├── current-state.md   # Stage 0 audit
│   ├── architecture.md    # Full architecture + decision rationale
│   ├── performance.md     # Performance analysis + P50/P95 estimates
│   ├── security.md        # OWASP Top 10 review + hardening checklist
│   ├── code-review.md     # AI-assisted code review findings
│   ├── retrospective.md   # Process + harness + AI collaboration reflection
│   └── harness-traces/    # TDD session traces (auth, LLM, ranker)
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py        # FastAPI app factory + lifespan
│       ├── config.py      # Pydantic settings from .env
│       ├── core/security.py   # JWT + bcrypt
│       ├── api/           # routes_auth, routes_trip, routes_health
│       ├── services/      # auth, trip, ranker, intent_parser, distance
│       ├── clients/       # llm, weather, places, overpass, geocode
│       ├── db/            # models, database, cache
│       ├── schemas/       # auth.py, trip.py
│       └── utils/logger.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api.js         # All backend API calls in one file
│       ├── context/AuthContext.jsx
│       ├── App.jsx
│       └── pages/         # LoginPage, DashboardPage, HistoryPage
└── tests/
    ├── conftest.py        # Fixtures: TestClient, registered_user, auth_headers
    ├── test_auth.py
    ├── test_trip.py
    ├── test_health.py
    └── services/
        ├── test_ranker.py
        └── test_intent_parser.py
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend |
| pip | latest | Backend deps |
| Node.js | 18+ | Frontend |
| npm | 9+ | Frontend deps |

External accounts (optional in dev — see Mock Mode below):
- [OpenWeatherMap API key](https://openweathermap.org/api) (free tier)
- [Foursquare API key](https://developer.foursquare.com/) (free tier)
- AWS account with Bedrock Nova Lite enabled in us-east-1

---

## Quick Start

### 1. Clone and navigate

```bash
cd LocalTravelSuggester_V2.0-main
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows:
# Windows(cmd):
.venv\Scripts\activate
# Windows(powershell):
.\.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# Edit .env — minimum required for dev (all others optional):
# SECRET_KEY=<any random string>
# LLM_MOCK=true   (skips AWS Bedrock; uses rule-based mock)
# OPENWEATHER_API_KEY=<your key>   (needed for real weather data)
```

### 3. Run the backend

```bash
# From the backend/ directory, with venv active:
uvicorn app.main:app --reload

# API available at: http://localhost:8000
# Interactive docs:  http://localhost:8000/docs
```

### 4. Frontend setup

```bash
# From the project root, in a new terminal:
cd frontend
npm install
npm run dev

# Frontend available at: http://localhost:5173
# (Vite proxies /api and /auth to http://localhost:8000)
```

---

## Running Tests

From the **project root** (not `backend/`):

```bash
# With venv active and pytest installed:
pytest

# With coverage report:
pytest --cov=app --cov-report=term-missing

# Run a specific file:
pytest tests/test_auth.py -v
```

**Expected output:** All tests pass, coverage ≥70%.

**Test environment is fully isolated:**
- In-memory SQLite (no file created, no cleanup needed)
- `LLM_MOCK=true` (no AWS calls)
- `FOURSQUARE_ENABLED=false` (no Foursquare calls)
- `respx` mocks for OpenWeatherMap and Overpass

---

## Mock Mode (No External APIs Needed)

Set these in `backend/.env` to run completely offline:

```env
LLM_MOCK=true
FOURSQUARE_ENABLED=false
```

With mock mode:
- LLM reasoning is generated by a local rule-based function (no AWS)
- Foursquare is skipped; Overpass (OpenStreetMap) is used for places
- Weather still requires an OpenWeatherMap API key, OR you can temporarily hardcode a mock in `weather_client.py`

---

## API Reference

Full interactive docs at `/docs` when the backend is running.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register a new user |
| POST | `/auth/login` | No | Login, returns JWT |
| GET | `/auth/me` | Yes | Current user profile |
| POST | `/suggest-trip` | Yes | Get AI trip recommendations |
| GET | `/history` | Yes | User's past queries |
| GET | `/health` | No | Liveness check |
| GET | `/health/detailed` | No | All dependency statuses |

**Authentication:** All protected endpoints require `Authorization: Bearer <token>` header.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT signing key — change in production |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | JWT expiry |
| `OPENWEATHER_API_KEY` | `None` | OpenWeatherMap API key |
| `FOURSQUARE_API_KEY` | `None` | Foursquare API key |
| `FOURSQUARE_ENABLED` | `true` | Set `false` to skip Foursquare |
| `LLM_MOCK` | `false` | Set `true` to skip AWS Bedrock |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | `None` | AWS credentials (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | `None` | AWS credentials |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | Bedrock model |
| `DATABASE_URL` | `sqlite:///./local_travel.db` | SQLite (dev) or PostgreSQL (prod) |
| `HTTP_TIMEOUT_SECONDS` | `10.0` | Timeout for external API calls |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Auth | JWT (python-jose) | Stateless; one-line dependency injection via `Depends()` |
| Password hashing | direct `bcrypt` (not passlib) | passlib 1.7.x is incompatible with bcrypt 4.x |
| LLM abstraction | Single `LLMClient` class | One provider, one mock — abstract class added no value |
| Frontend state | React Context + localStorage | 3 pages, one shared auth state — Redux is overkill |
| Database | SQLite (dev) / PostgreSQL (prod) | SQLAlchemy abstracts the difference; SQLite needs zero setup |
| Place fallback | Foursquare → Overpass | Overpass (OpenStreetMap) is free, rate-limit-free, globally available |

Full decision rationale with alternatives and tradeoffs: [`docs/architecture.md`](docs/architecture.md)

---

## Engineering Process

This project follows a structured 6-stage engineering process. For a full explanation of how AI tools were used at each stage, see [`docs/ai-workflow.md`](docs/ai-workflow.md).

- **Stage 0** — Audit (`docs/current-state.md`)
- **Stage 1** — Requirements (`specs/local-travel-suggester/spec.md`)
- **Stage 2** — Technical Plan (`specs/local-travel-suggester/plan.md`, `tasks.md`, `docs/architecture.md`)
- **Stage 3** — AI Tooling (`.cursor/rules/`, `AGENTS.md`)
- **Stage 4** — TDD Implementation (tests first, ≥70% coverage, `docs/harness-traces/`)
- **Stage 5** — Change Management (`openspec/changes/CHG-001`, `CHG-002`)
- **Stage 6** — QA (`docs/performance.md`, `docs/security.md`, `docs/code-review.md`)
