# CHG-002 — Simplify Budget Estimation

**Change ID:** CHG-002
**Type:** Feature Modification / Simplification
**Status:** Proposed
**Date:** 2026-05-25
**Requestor:** Technical review / Stage 5

---

## 1. Problem Statement

The current budget estimation (`services/budget.py`) provides:
- Entry fee from Foursquare price tier (1→₹50, 2→₹200, 3→₹500, 4→₹1200)
- Travel cost: distance × ₹24/km (Indian metro cab proxy)
- Total: entry + travel

**Issues:**
1. Foursquare's free-tier data often has `price_tier=null` for most venues, so entry is always ₹0
2. The ₹24/km cab rate is hardcoded and has no visible source or date
3. Overpass results (the OSM fallback) never include pricing — so in degraded mode, entry is always ₹0
4. The `note` field says "Indicative" but the UI renders it as a real number, potentially misleading users
5. Budget is displayed as a column in suggestions, adding UI clutter for unreliable data

**Result:** The feature produces near-zero entries in most cases and adds complexity without commensurate value.

---

## 2. Proposed Change

**Option A (chosen):** Remove the per-place budget estimation entirely. Remove `estimated_budget` from `PlaceSuggestion` schema and the budget column from the UI.

**Why Option A:** Budget estimation with missing data is worse than no budget estimation — it gives users false confidence in numbers that are frequently wrong. Removing it is honest and simplifies the API response.

**Simpler alternative (Option B):** Keep budget but make it optional, displayed only when price_tier is available.

**Why Option B was rejected:** Even when shown conditionally, the ₹24/km travel proxy is not a real estimate — it's a round-number approximation. The feature creates a support burden without clear value.

---

## 3. What Stays

- `distance_km` field stays on `PlaceSuggestion` — this is genuinely useful for planning
- The `price_tier` raw field from Foursquare is retained internally (not exposed in API) in case a future version adds a better pricing integration

---

## 4. Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Keep budget, add disclaimer UI | Users read numbers, not disclaimers |
| Fetch real entry prices from a third API | Adds another external dependency; Indian entry fees change frequently |
| Option B (conditional display) | Still shows unreliable numbers; adds conditional rendering complexity |
