## Context

The app persists each `/suggest-trip` call in `query_history` as a full `TripResponse` snapshot. Users can browse past queries on `/history` but cannot bookmark individual places. Favorites need their own table, access pattern (CRUD per place), and user isolation — separate from history (`docs/retrospective.md`).

Approved brainstorming design: `docs/superpowers/specs/2026-06-03-user-favorites-design.md`. This change uses a **flat column schema** (explicit in the change request) instead of a single `place_data` JSON blob — simpler queries and aligns with displayed fields on the favorites page.

## Goals / Non-Goals

**Goals:**

- Let authenticated users save a place from dashboard suggestion cards, list saved places, and remove saves.
- Enforce user isolation on all favorites endpoints.
- Return 409 on duplicate save; 404 (not 403) when DELETE targets a missing or other-user favorite.
- Follow project layer rules: routes → services → DB; tests before implementation.

**Non-Goals:**

- Favoriting from the History page (v1: dashboard only).
- Editing favorite metadata after save.
- Re-fetching live place data on list (snapshot at save time).
- Alembic migrations (`create_all()` on startup, same as existing tables).
- API versioning.

## Decisions

### 1. Separate `user_favorites` table (not `query_history`)

**Choice:** New table with one row per saved place.

**Alternatives rejected:**
- JSON flag inside `query_history.response` — requires full-table JSON scans; no clean delete/list.
- Shared table with nullable query columns — mixed responsibilities.

**Rationale:** Different granularity, schema, and access pattern from history.

### 2. Flat columns vs JSON blob

**Choice:** Store `place_name`, `city`, `lat`, `lng`, `categories` (JSON), `reasoning` as columns.

**Alternatives rejected:**
- Full `PlaceSuggestion` JSON in `place_data` — flexible but harder to index and query; overkill for v1 display needs.

**Rationale:** Matches fields shown on FavoritesPage; POST accepts full `PlaceSuggestion` from the client and flattens on save (`name` → `place_name`, `coords` → `lat`/`lng`, trip city → `city`).

### 3. Duplicate handling — 409 Conflict

**Choice:** Unique constraint on `(user_id, place_name)`; duplicate POST returns 409 with `"Place already saved"`.

**Alternatives rejected:**
- Upsert — hides duplicate from user; refreshes snapshot silently.
- Allow duplicates — cluttered list.

**Rationale:** Explicit UI feedback; approved in brainstorming.

### 4. Cross-user DELETE — 404 Not Found

**Choice:** Query `WHERE id = ? AND user_id = current_user.id`; zero rows → 404.

**Alternatives rejected:**
- 403 Forbidden — confirms the favorite ID exists for another user (enumeration risk).

**Rationale:** Documented in `docs/security.md` A01; consistent with history scoping pattern.

### 5. Service layer for business logic

**Choice:** `favorites_service.py` with `create_favorite`, `list_favorites`, `delete_favorite`. Routes translate exceptions to HTTP status codes.

**Rationale:** Matches `trip_service.py` / `auth_service.py` pattern; routes stay thin.

### 6. TDD order

**Choice:** Write all `tests/test_favorites.py` cases first; confirm red; then implement model → schemas → service → routes → `main.py`.

**Rationale:** Project convention (`AGENTS.md`, `docs/ai-workflow.md`).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Same place name in different cities blocks second save | Accept for demo scope; user sees 409; documented tradeoff |
| Flat schema omits `distance_km`, `score`, `website` at save time | v1 FavoritesPage shows stored fields only; extend columns later if needed |
| Stale reasoning/coords after re-search | Snapshot by design; user deletes and re-saves to refresh |
| ID enumeration via DELETE | 404 for both missing and cross-user IDs |

## Migration Plan

1. Deploy backend + frontend together (additive — no breaking API changes).
2. Table created on app startup via `Base.metadata.create_all()`.
3. Rollback: revert PR; drop table manually if needed (no data migration).

## Open Questions

None — scope approved in brainstorming and design doc.
