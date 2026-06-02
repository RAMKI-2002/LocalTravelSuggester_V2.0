# User Favorites for Place Suggestions

**Date:** 2026-06-03  
**Status:** Approved for implementation  
**Change type:** Additive feature (new table, routes, page)

---

## Problem

Users can run trip suggestions and browse history, but cannot save individual places they like. A place worth revisiting is buried inside a `query_history` blob and lost once newer queries pile up.

## Goal

Let authenticated users save individual `PlaceSuggestion` items from trip results, list their saved places, and remove saves. Favorites are user-scoped and isolated from other accounts.

## Non-Goals

- Favoriting from the History page (v1: dashboard suggestion cards only).
- Editing favorite metadata (notes, tags, custom labels).
- Re-fetching live place data on list — store a snapshot at save time.
- Sharing favorites between users or public profiles.
- API versioning — additive endpoints only.

---

## Why a Separate `user_favorites` Table (Not `query_history`)

| Concern | `query_history` | `user_favorites` |
|---------|-----------------|------------------|
| Granularity | One row per `/suggest-trip` call | One row per saved place |
| Access pattern | Chronological query summaries | CRUD on individual places |
| Schema | Full `TripResponse` JSON blob | Place snapshot + optional source city |

Extending `query_history` would require scanning and mutating JSON blobs to list or delete favorites, with no clean index on `(user_id, place)`. Different access pattern, different schema — do not mix (`docs/retrospective.md`).

---

## Database

### Table: `user_favorites`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Auto-increment |
| `user_id` | Integer FK → `users.id` | Indexed, `ON DELETE CASCADE` |
| `place_name` | String(256) | Denormalized for display and dedup key |
| `place_data` | JSON | Full `PlaceSuggestion` snapshot at save time |
| `source_city` | String(128), nullable | Trip city when the user clicked save |
| `created_at` | DateTime(timezone=True) | `server_default=func.now()` |

### Unique constraint

`(user_id, place_name)` — one saved row per place name per user.

**Rationale:** Simple dedup without parsing JSON coordinates. Acceptable for demo scope; two different venues with identical names in different cities would conflict (edge case — user sees 409).

### ORM

- New `UserFavorite` model in `backend/app/db/models.py`.
- Add `User.favorites` relationship with `cascade="all, delete-orphan"`.
- Table created via existing `Base.metadata.create_all()` on startup (no Alembic).

---

## API Contracts

All endpoints require `Authorization: Bearer <token>`. Unauthenticated requests return **401**.

### POST /favorites

**Request body:**

```json
{
  "place": {
    "name": "Hussain Sagar Lake",
    "description": "...",
    "categories": ["lake", "park"],
    "reasoning": "Perfect for a peaceful evening…",
    "coords": { "lat": 17.42, "lng": 78.47 },
    "distance_km": 12.3,
    "score": 0.82,
    "website": null,
    "address": "..."
  },
  "source_city": "Hyderabad"
}
```

- `place` — required; validated as `PlaceSuggestion` (reuse schema from `schemas/trip.py` or mirror in `schemas/favorites.py`).
- `source_city` — optional string, max 128 chars.

**Responses:**

| Status | Meaning |
|--------|---------|
| `201 Created` | Favorite saved; body includes `{ id, place_name, place_data, source_city, created_at }` |
| `401 Unauthorized` | Missing or invalid token |
| `409 Conflict` | Duplicate — same `user_id` + `place_name` already exists; detail: `"Place already saved"` |
| `422 Unprocessable Entity` | Invalid `place` payload |

### GET /favorites?limit=20

**Query params:** `limit` — integer, default 20, range 1–50.

**Response:**

```json
{
  "count": 2,
  "items": [
    {
      "id": 1,
      "place_name": "Hussain Sagar Lake",
      "place_data": { "...": "PlaceSuggestion snapshot" },
      "source_city": "Hyderabad",
      "created_at": "2026-06-03T10:00:00+00:00"
    }
  ]
}
```

- Filter: `WHERE user_id = current_user.id`.
- Order: `created_at DESC`.

### DELETE /favorites/{id}

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Favorite deleted |
| `401 Unauthorized` | Missing or invalid token |
| `404 Not Found` | No row with that `id` **and** `user_id = current_user.id` |

**Security — 404 not 403:** When User B attempts to delete User A's favorite ID, return **404** (not 403) to prevent ID enumeration. Same rule applies to any future GET-by-id endpoint (`docs/security.md` A01).

---

## Backend Layout

Follow existing project folder rules:

| File | Responsibility |
|------|----------------|
| `backend/app/db/models.py` | `UserFavorite` model + `User.favorites` relationship |
| `backend/app/schemas/favorites.py` | `FavoriteCreate`, `FavoriteItem`, `FavoriteListResponse` |
| `backend/app/services/favorites_service.py` | `create_favorite`, `list_favorites`, `delete_favorite` — raises `ValueError` for duplicates |
| `backend/app/api/routes_favorites.py` | HTTP only; translates `ValueError` → 409, missing row → 404 |
| `backend/app/main.py` | Register `routes_favorites` router |

Service layer owns business rules (duplicate check). Routes do not import SQLAlchemy query logic directly beyond dependency injection.

---

## Frontend

### New page: `FavoritesPage.jsx` (`/favorites`)

- Protected route (same pattern as History).
- On mount: `GET /favorites?limit=20`.
- Each item: place name, categories, reasoning, distance, score, source city, saved date.
- Unfavorite button → `DELETE /favorites/{id}` → remove from list on 204.
- Empty state: "No saved places yet — find suggestions on the Dashboard."

### Dashboard changes: `DashboardPage.jsx`

- Add heart/save button on each `SuggestionCard`.
- On click: `POST /favorites` with suggestion payload + `result.city` as `source_city`.
- On `201`: toggle heart filled / show brief "Saved" feedback.
- On `409`: show "Already saved" message (no error throw).
- On other errors: show error toast/inline message.

### Navigation and API

| File | Change |
|------|--------|
| `App.jsx` | Nav link "Favorites" + `<Route path="/favorites">` |
| `api.js` | `addFavorite(place, sourceCity)`, `getFavorites(limit)`, `deleteFavorite(id)` |
| `vite.config.js` | Proxy `/favorites` → `http://localhost:8000` |

---

## Data Flow

```
Dashboard SuggestionCard [♥]
  → POST /favorites { place, source_city }
  → favorites_service.create_favorite(user_id, ...)
  → INSERT user_favorites (or 409 if duplicate)

FavoritesPage mount
  → GET /favorites?limit=20
  → SELECT WHERE user_id = current_user.id ORDER BY created_at DESC

FavoritesPage [Remove]
  → DELETE /favorites/{id}
  → DELETE WHERE id = ? AND user_id = current_user.id (404 if 0 rows)
```

---

## Tests (`tests/test_favorites.py`)

DB-only tests — no external HTTP mocks.

| Test | Asserts |
|------|---------|
| `test_post_favorite_without_auth_returns_401` | Auth gate on POST |
| `test_get_favorites_without_auth_returns_401` | Auth gate on GET |
| `test_delete_favorite_without_auth_returns_401` | Auth gate on DELETE |
| `test_post_favorite_saves_and_returns_201` | Happy path; response includes `id`, `place_name` |
| `test_post_duplicate_favorite_returns_409` | Same user + same `place.name` → 409 |
| `test_get_favorites_returns_only_current_user_items` | User A saves 2, User B saves 1; each GET returns own count only |
| `test_user_b_cannot_delete_user_a_favorite_returns_404` | User B deletes A's ID → 404; A's GET still shows the item |
| `test_delete_own_favorite_returns_204` | Owner delete succeeds; subsequent GET excludes it |
| `test_delete_nonexistent_favorite_returns_404` | Bogus ID → 404 |

Pattern mirrors `test_history_returns_user_scoped_results` in `tests/test_trip.py`.

---

## Documentation Updates (During Implementation)

| Document | Update |
|----------|--------|
| `README.md` | What It Does; architecture diagram; project structure; API table (+3 rows) |
| `docs/architecture.md` | Frontend tree (4th page); API routes; DB table list |
| `docs/security.md` | A01: implement `/favorites` scoping; 404-on-cross-user DELETE |
| `docs/performance.md` | Index note: `user_favorites.user_id` |
| `docs/design/README.md` | Page 4 wireframe; nav links |
| `docs/current-state.md` | API table + feature list |
| `openspec/specs/user-favorites/spec.md` | Capability spec (requirements + scenarios) |

---

## Design Decisions

| Decision | Choice | Alternative rejected | Tradeoff |
|----------|--------|---------------------|----------|
| Storage | Separate `user_favorites` table | JSON flags in `query_history.response` | Extra table, but clean queries and indexes |
| Duplicate save | **409 Conflict** | Upsert (refresh snapshot) | Explicit UI message; user must delete then re-save to refresh data |
| Cross-user DELETE | **404 Not Found** | 403 Forbidden | Prevents favorite ID enumeration |
| Dedup key | `(user_id, place_name)` | `(user_id, name, lat, lng)` | Simpler constraint; rare name collision across cities |
| Place data | JSON snapshot | Re-query places API on list | Stale coords/description possible; no external deps on read |

---

## Error Handling

| Layer | Pattern |
|-------|---------|
| Service | `ValueError("Place already saved")` on duplicate |
| Route | `ValueError` → HTTP 409; missing row → HTTP 404; auth via `get_current_user` → 401 |
| Frontend | 409 → friendly "Already saved"; other errors → `handleResponse` throw |

---

## Out of Scope (Explicit)

- Refreshing a favorite when the same place is saved again (409 blocks it).
- Bulk delete or "clear all favorites".
- Favorite count badge in nav.
- OpenSpec archive until implementation and tests pass.
