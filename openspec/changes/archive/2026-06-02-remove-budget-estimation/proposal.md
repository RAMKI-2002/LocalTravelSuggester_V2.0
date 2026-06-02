## Why

Per-place budget estimation produces misleading values — especially ₹0 entry fees when Overpass-sourced places lack pricing data. Showing a wrong number is worse than showing nothing. The approved design rationale is documented in `docs/superpowers/specs/2026-06-02-remove-budget-estimation-design.md`.

## What Changes

- **BREAKING:** Remove `estimated_budget` and the `Budget` model from `PlaceSuggestion` in the `/suggest-trip` API response.
- Delete `backend/app/services/budget.py` and all budget enrichment in `trip_service.py`.
- Remove ₹ budget display from `DashboardPage.jsx` suggestion cards.
- Remove `price_tier` from normalized place dicts in `places_client.py` and `overpass_client.py`.
- Remove `"price"` from the Foursquare `FIELDS` request (only used for `price_tier`).
- Update project docs that reference budget estimation.

## Capabilities

### New Capabilities

- `trip-suggestion`: Defines the `/suggest-trip` response contract for place suggestions — fields included, fields excluded, and unchanged behavior (distance, reasoning, ranking).

### Modified Capabilities

<!-- No existing openspec/specs/ baseline. This change establishes the trip-suggestion capability spec. -->

## Impact

- **API:** `POST /suggest-trip` — `suggestions[].estimated_budget` removed (breaking; deploy backend + frontend together).
- **Backend:** `schemas/trip.py`, `services/trip_service.py`, `services/budget.py` (delete), `clients/places_client.py`, `clients/overpass_client.py`.
- **Frontend:** `frontend/src/pages/DashboardPage.jsx`.
- **Tests:** `tests/test_trip.py` — add regression assertion that `estimated_budget` is absent.
- **Unchanged:** `distance_km`, ranker proximity scoring, LLM curate/reasoning, map markers, `/history`, weather, auth.
- **Stored data:** Existing `query_history.response` JSON may retain old `estimated_budget` fields; no migration required.
