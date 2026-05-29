# CHG-002 — Implementation Tasks

## Backend Tasks

**CHG-002-B1** — Remove `Budget` schema from `backend/app/schemas/trip.py` (0.3h)
- Delete `Budget` class
- Remove `estimated_budget: Budget` field from `PlaceSuggestion`

**CHG-002-B2** — Remove budget import and call from `backend/app/services/trip_service.py` (0.3h)
- Remove `from app.services.budget import estimate_budget`
- Remove `place["_budget"] = estimate_budget(...)` call in enrich step
- Remove `estimated_budget=Budget(...)` from `PlaceSuggestion` constructor in `_build_response`

**CHG-002-B3** — Delete `backend/app/services/budget.py` (0.1h)

**CHG-002-B4** — Update tests `tests/test_trip.py` (0.3h)
- Remove assertions referencing `estimated_budget`
- Verify tests still pass after change

## Frontend Tasks

**CHG-002-F1** — Remove budget display from `DashboardPage.jsx` `SuggestionCard` (0.3h)
- Remove `💰 ₹{suggestion.estimated_budget.total}` span

## Documentation Tasks

**CHG-002-D1** — Update `docs/architecture.md` to remove budget estimation from pipeline description (0.2h)

## Estimated Total: ~1.5 hours

## Rollback Plan

The `budget.py` file is tracked in git. Rollback is:
```
git revert <commit>
```
Or restore by re-adding the import and field in 3 files. No database migration needed (budget was never stored).
