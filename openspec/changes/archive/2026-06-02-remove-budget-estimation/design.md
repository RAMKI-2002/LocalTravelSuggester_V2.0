## Context

The trip suggestion pipeline currently enriches each place with a coarse INR budget estimate (`services/budget.py`) derived from Foursquare `price_tier` and user distance. Overpass-sourced places always have `price_tier=None`, producing ₹0 entry fees that mislead users. The approved brainstorming design is at `docs/superpowers/specs/2026-06-02-remove-budget-estimation-design.md`.

Current enrich step in `trip_service.py` (step `[7]`):

1. Compute `_budget` via `estimate_budget()` for every final place
2. Generate LLM reasoning for places missing `_reasoning`

After this change, step `[7]` performs reasoning-only enrichment.

## Goals / Non-Goals

**Goals:**

- Remove `estimated_budget` from the public API and all computation paths
- Delete dead code: `budget.py`, `Budget` schema, `price_tier` in place clients
- Remove budget UI from dashboard suggestion cards
- Preserve `distance_km`, ranker scoring, LLM curate/reasoning, map, and history behavior

**Non-Goals:**

- Migrate stored `query_history.response` JSON
- API versioning or nullable backward-compatible fields
- Remove "budget-friendly" from intent parsing (semantic preference, not cost display)
- Change Foursquare fields beyond removing `"price"`

## Decisions

### 1. Full removal over deprecation

**Choice:** Delete `estimated_budget` from schema entirely (Approach A).

**Alternatives rejected:**
- Nullable field always `null` — dead schema, confuses API consumers
- UI-only removal — API still returns misleading ₹0 values

**Rationale:** Matches retrospective decision; simplest correct outcome.

### 2. Remove `price_tier` from client normalization

**Choice:** Drop `price_tier` from `_normalise()` in both `places_client.py` and `overpass_client.py`; remove `"price"` from Foursquare `FIELDS`.

**Rationale:** `price_tier` has no consumer after `budget.py` is deleted. Requesting `"price"` from Foursquare wastes payload for unused data.

### 3. Keep `distance_km` and dual internal distances

**Choice:** No changes to `_distance_km` (ranker/filter anchor) or `_distance_km_user` (API display field).

**Rationale:** Distance is independent of budget; ranker and UI depend on it.

### 4. Coordinated monorepo deploy

**Choice:** Ship backend + frontend together; no API version bump.

**Rationale:** Single repo, single frontend consumer; optional chaining on frontend already prevents crashes but field should disappear from both sides simultaneously.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| External clients depend on `estimated_budget` | Document as **BREAKING** in proposal; no known external consumers |
| Old history JSON contains budget fields | History endpoint ignores them; no re-validation on read |
| Accidental reintroduction via Foursquare `price` field | Remove from `FIELDS` and `_normalise()` in same change |
| Test gap if budget field silently reappears | Add assertion `"estimated_budget" not in s` in happy-path test |

## Migration Plan

1. Merge backend + frontend changes in one PR
2. Deploy both services together (no DB migration)
3. Rollback: revert PR; no data cleanup needed

## Open Questions

None — scope approved in brainstorming.
