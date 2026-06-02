# Remove Per-Place Budget Estimation

**Date:** 2026-06-02  
**Status:** Approved for implementation  
**Change type:** Breaking API change (coordinated monorepo deploy)

---

## Problem

Per-place budget estimation produces misleading values — especially ₹0 entry fees when `price_tier` is missing from Overpass-sourced places. Showing a wrong number is worse than showing nothing (`docs/retrospective.md`).

## Goal

Remove budget estimation from the trip suggestion pipeline, API response, and UI. Also remove upstream `price_tier` collection since it exists solely to feed the budget estimator.

## Non-Goals

- Migrating or rewriting stored `query_history.response` JSON (old rows may retain `estimated_budget`; harmless).
- API versioning or backward-compatible nullable fields.
- Removing user preference keywords like "budget-friendly" from intent parsing (unrelated to per-place cost display).

---

## What Stays

| Field / behavior | Reason |
|------------------|--------|
| `distance_km` on `PlaceSuggestion` | User-facing display (cards + map popups) |
| `_distance_km` in ranker | Anchor-based proximity scoring |
| `_distance_km_user` internal field | Source for API `distance_km` when user locality is geocoded |
| LLM curate + per-place reasoning | Unrelated to budget |
| Weather, coords, score, categories, website, address | Core suggestion payload |

---

## What Gets Removed

### API schema (`backend/app/schemas/trip.py`)

- Delete `Budget` Pydantic model.
- Remove `estimated_budget: Budget` from `PlaceSuggestion`.

### Service layer

- **Delete** `backend/app/services/budget.py`.
- **`trip_service.py`:**
  - Remove `estimate_budget` import.
  - Step `[7] Enrich`: drop budget loop; keep reasoning-only enrichment.
  - `_build_response`: remove `estimated_budget` mapping.
  - Update module docstring (step `[7]` description).

### Place clients

- **`places_client.py`:**
  - Remove `"price"` from Foursquare `FIELDS` request.
  - Remove `"price_tier"` key from `_normalise()` return dict.
- **`overpass_client.py`:**
  - Remove `"price_tier": None` from normalized place dict.

### Frontend

- **`DashboardPage.jsx`:** Remove ₹ budget display from `SuggestionCard` (conditional on `estimated_budget?.total`).

### Documentation (align during implementation)

- `specs/local-travel-suggester/plan.md` — example JSON
- `specs/local-travel-suggester/tasks.md` — render checklist
- `docs/architecture.md`, `docs/design/README.md`, `docs/current-state.md`
- `README.md` — services folder blurb mentioning `budget.py`

---

## Data Flow (After)

```
Final places shortlist
  → LLM reasoning (if missing)
  → _build_response → PlaceSuggestion (no budget fields)
  → TripResponse → client
```

Distance enrichment (steps `[4]`–`[5]`) is unchanged.

---

## Breaking Change Assessment

| Consumer | Impact |
|----------|--------|
| `POST /suggest-trip` response | `suggestions[].estimated_budget` removed |
| In-repo frontend | Remove display lines; optional chaining already prevents crashes |
| `GET /history` | No impact (never exposed budget) |
| Stored history JSON | Old records may contain field; ignored by history endpoint |
| External API clients | Breaking if any depend on `estimated_budget` |

**Deploy:** Ship backend and frontend together. No API version bump.

---

## Testing

### Existing tests (should pass unchanged)

- `tests/test_trip.py` — asserts `name`, `reasoning`, `coords` only
- `tests/services/test_ranker.py` — uses `_distance_km`, not budget

### Recommended addition

In `test_suggest_trip_happy_path`, assert `"estimated_budget" not in s` for each suggestion.

### Verification command

```bash
pytest tests/ -v
```

---

## File Checklist

| File | Action |
|------|--------|
| `backend/app/schemas/trip.py` | Edit |
| `backend/app/services/trip_service.py` | Edit |
| `backend/app/services/budget.py` | Delete |
| `backend/app/clients/places_client.py` | Edit |
| `backend/app/clients/overpass_client.py` | Edit |
| `frontend/src/pages/DashboardPage.jsx` | Edit |
| `tests/test_trip.py` | Edit (optional assertion) |
| Docs listed above | Edit |

---

## Design Decision Record

**Why full removal (Approach A)?**  
Partial deprecation (nullable `estimated_budget`) leaves dead schema and confuses consumers. UI-only removal keeps misleading API data. Full removal matches the retrospective rationale.

**Why remove `price_tier` from clients?**  
It is only consumed by `estimate_budget()`. Keeping it adds dead metadata to every place dict with no current consumer.

**Why not migrate history JSON?**  
History endpoint reads summary fields only (`top_suggestion` name, counts). Stored full responses are not re-validated against current schema.
