## 1. Tests (TDD — red first)

- [x] 1.1 Add regression assertion to `tests/test_trip.py` happy path: `assert "estimated_budget" not in s` for each suggestion
- [x] 1.2 Run `pytest tests/test_trip.py::test_suggest_trip_happy_path -v` and confirm FAIL (field still present)

## 2. Backend — atomic removal

- [x] 2.1 In `trip_service.py`: remove `estimate_budget` import, budget enrich loop, `estimated_budget` mapping, and `Budget` from schema imports; update step `[7]` docstring to reasoning-only
- [x] 2.2 In `schemas/trip.py`: remove `Budget` class and `estimated_budget` from `PlaceSuggestion`
- [x] 2.3 Delete `backend/app/services/budget.py`

## 3. Place client normalization

- [x] 3.1 In `places_client.py`: remove `"price"` from `FIELDS` and remove `price_tier` from `_normalise()` return dict
- [x] 3.2 In `overpass_client.py`: remove `price_tier` from normalized place dict

## 4. Frontend

- [x] 4.1 Remove ₹ budget display from `SuggestionCard` in `frontend/src/pages/DashboardPage.jsx`

## 5. Verification

- [x] 5.1 Run `pytest tests/ -v` and confirm all tests pass
- [x] 5.2 Grep codebase for stray references: `estimate_budget`, `from app.services.budget`, `price_tier`, `estimated_budget` (expect zero hits outside docs/changelog/openspec)

## 6. Documentation alignment

- [x] 6.1 Update `specs/local-travel-suggester/plan.md` — example JSON, services table, and pipeline diagram
- [x] 6.2 Remove budget from render checklist in `specs/local-travel-suggester/tasks.md`
- [x] 6.3 Update `docs/architecture.md`, `docs/design/README.md`, `docs/current-state.md`, and `README.md` service list
