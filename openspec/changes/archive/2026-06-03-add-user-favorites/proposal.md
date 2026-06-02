## Why

Users cannot save a specific place from trip suggestion results. `query_history` stores whole queries as JSON blobs, not individual places — so a place worth revisiting is buried and lost as new searches pile up. Approved design rationale: `docs/superpowers/specs/2026-06-03-user-favorites-design.md`.

## What Changes

- Add `user_favorites` table with flat place columns (`place_name`, `city`, `lat`, `lng`, `categories`, `reasoning`) scoped by `user_id`.
- Add authenticated REST endpoints: `POST /favorites`, `GET /favorites`, `DELETE /favorites/{id}`.
- Duplicate save for same user + place name returns **409 Conflict** (`"Place already saved"`).
- Cross-user or missing favorite on DELETE returns **404 Not Found** (not 403) to prevent ID enumeration.
- Frontend: heart/save on `DashboardPage` suggestion cards; new `FavoritesPage`; API helpers in `api.js`; route + nav in `App.jsx`.
- TDD: `tests/test_favorites.py` written **before** route implementation.
- Documentation updates across README and `docs/`.

## Capabilities

### New Capabilities

- `user-favorites`: Persist, list, and delete user-scoped saved places from trip suggestions; dashboard save affordance; favorites page UI; auth isolation and duplicate handling.

### Modified Capabilities

<!-- No changes to trip-suggestion response contract or ranking behavior. -->

## Impact

- **API:** Three new endpoints under `/favorites` (all JWT-protected via `get_current_user`).
- **Backend:** `db/models.py`, new `schemas/favorites.py`, `services/favorites_service.py`, `api/routes_favorites.py`, `main.py` router registration.
- **Frontend:** `api.js`, `DashboardPage.jsx`, new `FavoritesPage.jsx`, `App.jsx`, `vite.config.js` proxy.
- **Tests:** New `tests/test_favorites.py` (DB-only; no external HTTP mocks).
- **Docs:** `README.md`, `docs/architecture.md`, `docs/security.md`, `docs/current-state.md`, `docs/design/README.md`, `docs/performance.md`; grep audit for stale references.
- **Unchanged:** `/suggest-trip` pipeline, `/history`, auth flow, place clients, ranker, LLM.
