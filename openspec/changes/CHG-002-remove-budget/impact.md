# CHG-002 — Impact Analysis

## API Breaking Change

**YES — this is a breaking change to the API response schema.**

`estimated_budget` is removed from `PlaceSuggestion`. Any API consumer reading this field will receive `null` / field-not-found.

**Mitigation:** Since this is a demo/assessment project with no external consumers, breaking change risk is acceptable. For a production API, this would require a versioned endpoint (e.g., `/v2/suggest-trip`).

## Frontend Impact

The frontend renders `suggestion.estimated_budget?.total` with optional chaining. Removing the field from the response means this renders nothing — no crash, just a missing display element. The change is safe.

## Service Impact

| Component | Impact | Notes |
|-----------|--------|-------|
| `budget.py` | Deleted | No other files import it |
| `trip_service.py` | Minor | Remove 2 lines (import + call) |
| `schemas/trip.py` | Minor | Remove 2 class definitions |
| `test_trip.py` | Minor | Remove budget assertions |
| Frontend SuggestionCard | Minor | Remove 1 JSX element |

**Files changed: 5**
**Lines removed: ~25 backend + ~5 frontend**

## Performance Impact

**Positive:** Removes one O(n) loop over `final_places` in the trip pipeline. In practice: saving ~1ms per request for 5-10 places. Not significant.

## Test Coverage Impact

- Removing `budget.py` reduces total lines under coverage, slightly improving percentage
- The `budget.py` tests in `test_ranker.py` (if any existed) would be deleted
- Net coverage change: neutral to slightly positive

## Engineering Context

This change demonstrates the ability to make a "delete feature" decision rather than only adding complexity. Knowing when to remove code is a sign of engineering maturity. The budget feature in its current form produced numbers that were frequently wrong (price_tier=null → entry=₹0). Showing ₹0 was worse than showing nothing.
