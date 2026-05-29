# CHG-002 — Spec Diff

Changes to `specs/local-travel-suggester/spec.md` and `specs/local-travel-suggester/plan.md`

---

## API Contract — MODIFIED

```diff
  POST /suggest-trip → PlaceSuggestion:
    name: str
    description: str
    categories: list[str]
    reasoning: str
    coords: Coords
    distance_km: float | null
-   estimated_budget: Budget   ← REMOVED
    score: float
    website: str | null
    address: str | null
```

## Schemas — MODIFIED

```diff
- class Budget(BaseModel):
-     currency: str = "INR"
-     entry: int = 0
-     travel: int | None = None
-     total: int | None = None
-     note: str = ""

  class PlaceSuggestion(BaseModel):
      name: str
      description: str
      categories: list[str]
      reasoning: str
      coords: Coords
      distance_km: float | None
-     estimated_budget: Budget    ← REMOVED
      score: float
      website: str | None
      address: str | None
```

## Services — REMOVED

```diff
- backend/app/services/budget.py   ← file deleted
```

## Trip Service — MODIFIED

```diff
  # [7] Enrich: budget + per-place reasoning
  for place in final_places:
-     place["_budget"] = estimate_budget(place, place.get("_distance_km_user"))
      ...

- from app.services.budget import estimate_budget
```

## Frontend — MODIFIED

```diff
  function SuggestionCard({ suggestion, index }) {
    ...
-   {suggestion.estimated_budget?.total != null && (
-     <span>💰 ₹{suggestion.estimated_budget.total}</span>
-   )}
    {suggestion.distance_km != null && <span>📍 {suggestion.distance_km.toFixed(1)} km</span>}
```

## Acceptance Criteria — REMOVED

```diff
- Each suggestion includes: name, description, categories, AI reasoning, coordinates,
- distance (if locality provided)
+ Each suggestion includes: name, description, categories, AI reasoning, coordinates,
+ distance (if locality provided)
- (budget removed from this list)
```
