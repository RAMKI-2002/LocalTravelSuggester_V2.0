# Task Breakdown — Local Travel Suggester

**Stage:** 2 — Task Breakdown
**Date:** 2026-05-25
**Sizing:** Each task = 1–4 hours

---

## Task Groups

### Group A: Project Scaffold (2h)

**A-01** — Create full folder structure
- Create `backend/`, `frontend/`, `tests/`, `docs/`, `specs/`, `openspec/` directories
- Move existing Python code into `backend/app/`
- Verify existing code still imports correctly after move

**A-02** — Backend dependencies
- Update `backend/requirements.txt` with new deps: `python-jose[cryptography]`, `passlib[bcrypt]`, `pytest-cov`
- Add `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_HOURS` to `backend/.env.example`
- Verify `pip install -r requirements.txt` succeeds

**A-03** — Frontend scaffold
- `npm create vite@latest frontend -- --template react`
- Install Tailwind CSS: `npm install -D tailwindcss postcss autoprefixer`
- Install routing and map: `npm install react-router-dom react-leaflet leaflet`
- Verify `npm run dev` starts successfully

---

### Group B: Backend Auth (3h)

**B-01** — Write auth tests first (TDD)
- `tests/test_auth.py`: register success, duplicate email 409, login success, login wrong password 401, /me with valid token, /me with no token 401
- All tests should FAIL at this point (no implementation yet)

**B-02** — User model + DB migration
- Add `User` ORM model to `backend/app/db/models.py`
- Add `user_id` FK to `QueryHistory`
- Verify `init_db()` creates the new `users` table

**B-03** — Auth schemas
- Create `backend/app/schemas/auth.py`: `UserCreate`, `UserLogin`, `UserResponse`, `Token`

**B-04** — Security module
- Create `backend/app/core/security.py`:
  - `hash_password(plain: str) -> str`
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(user_id: int) -> str`
  - `get_current_user(token: str, db: Session) -> User` — FastAPI dependency

**B-05** — Auth service + routes
- Create `backend/app/services/auth_service.py`: `register_user()`, `authenticate_user()`
- Create `backend/app/api/routes_auth.py`: POST /auth/register, POST /auth/login, GET /auth/me
- Register router in `main.py`
- Run tests from B-01 → all should pass

---

### Group C: Backend LLM Simplification (2h)

**C-01** — Flatten LLM client
- Remove `LLMProvider` abstract base class
- Remove `BedrockLLMProvider` and `MockLLMProvider` as separate classes
- Create single `LLMClient` class with `_mock: bool` flag
- Keep same 3 public methods: `curate_places`, `extract_intent`, `generate_place_reasoning`
- Remove `get_llm_provider()` factory; use `LLMClient()` directly

**C-02** — Remove http_base.py
- Inline `httpx.AsyncClient` into each client that uses it
- Remove `http_base.py` and `UpstreamError` import
- Define `UpstreamError` locally in each client or in a shared `exceptions.py`
- Verify all clients still work

---

### Group D: Trip Routes Update (2h)

**D-01** — Write trip tests first (TDD)
- `tests/test_trip.py`: happy path with mock LLM + mock HTTP, unauthenticated 401, missing city 422, history endpoint returns user-scoped results
- Mock all external HTTP calls with `respx`

**D-02** — Add auth to trip routes
- `POST /suggest-trip` requires `Depends(get_current_user)` — attach `user_id` to history row
- `GET /history` requires `Depends(get_current_user)` — filter by `user_id`
- Run tests from D-01 → all should pass

---

### Group E: Backend Health + Tests (2h)

**E-01** — Simplify health endpoint
- Remove `log_buffer.py` and `/logs` endpoint (simplification)
- Keep `/health` and `/health/detailed`
- Update health checks to work with new flattened LLM client

**E-02** — Write health tests
- `tests/test_health.py`: /health returns 200, /health/detailed contains `checks` key
- `tests/services/test_ranker.py`: score_place weather scenarios, rank_places with diversity cap
- `tests/services/test_intent_parser.py`: rule hits for each category, default fallback

**E-03** — Coverage verification
- Run `pytest --cov=app --cov-report=term-missing`
- Confirm coverage ≥ 70%
- Fix any gaps by adding targeted tests

---

### Group F: Frontend — Auth Pages (3h)

**F-01** — Auth context + routing
- Create `frontend/src/context/AuthContext.jsx`: token in localStorage, `login()`, `logout()`, `user` state
- Create `frontend/src/App.jsx`: BrowserRouter, protected route guard (redirect to /login if no token)
- Create `frontend/src/api.js`: all fetch calls with Authorization header injection

**F-02** — Login / Register page
- Create `frontend/src/pages/LoginPage.jsx`
- Two tabs: Register (username, email, password) and Login (email, password)
- On success: store token in context, redirect to dashboard
- Tailwind styling: centered card, error display

---

### Group G: Frontend — Dashboard Page (4h)

**G-01** — Trip form
- City input, preference textarea, locality input, max_results selector
- Loading state, error display
- Call `POST /suggest-trip` on submit

**G-02** — Suggestions list
- Render each suggestion: name, categories chips, reasoning, distance
- Weather banner at top
- Meta info: elapsed time, cache hits, degraded warnings

**G-03** — Map integration
- react-leaflet MapContainer with OSM tiles
- Numbered markers for suggestions
- User locality marker (different colour)
- Fit map bounds to all markers on new results

---

### Group H: Frontend — History Page (2h)

**H-01** — History list
- Call `GET /history?limit=20` on mount
- Display: city, preference, date, number of suggestions returned
- Link or expand to show suggestion names from that query

**H-02** — Navigation + Layout
- Top nav bar: app name, Dashboard link, History link, Logout button
- Responsive layout (Tailwind `lg:grid-cols-2` for form + map side by side)

---

### Group I: Documentation (3h)

**I-01** — docs/architecture.md with Mermaid diagrams
**I-02** — docs/harness-traces/ (3 representative trace files)
**I-03** — docs/ stage documentation for stages 2, 3, 4
**I-04** — README.md with setup instructions
**I-05** — AGENTS.md

---

## Test Scenarios Per Task

| Task | Test Scenario | Pass Condition |
|------|--------------|----------------|
| B-01 | POST /auth/register with valid data | 200 + access_token |
| B-01 | POST /auth/register duplicate email | 409 Conflict |
| B-01 | POST /auth/login wrong password | 401 Unauthorized |
| B-01 | GET /auth/me with valid token | 200 + user data |
| D-01 | POST /suggest-trip no auth header | 401 Unauthorized |
| D-01 | POST /suggest-trip missing city | 422 Unprocessable Entity |
| D-01 | POST /suggest-trip valid | 200 + suggestions list |
| D-01 | GET /history user A cannot see user B history | results scoped by user_id |
| E-02 | GET /health | 200, `{"status": "ok"}` |
| E-02 | GET /health/detailed | 200, contains `checks` dict |
| E-02 | rank_places with rainy weather | indoor places ranked higher |
| E-02 | rank_places diversity cap | max 2 per category in results |
| E-02 | parse_intent "want to eat food" | category = "food" |
| E-02 | parse_intent empty string | category = "tourist" (default) |
