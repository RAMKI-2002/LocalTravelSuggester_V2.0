# Harness Trace 03 — TDD: Ranker Unit Tests

**Task:** E-02 Write ranker tests
**Date:** 2026-05-25
**Agent Role:** Test Writer → Code Reviewer

---

## Brainstorm Phase

**Context:** The ranker is a pure function — no HTTP, no database. It takes a list of places + weather + preference and returns a scored, ranked, diversity-capped list. This is an ideal TDD candidate because:
- Deterministic: same input always produces same output
- No mocks needed: no external dependencies
- Directly testable: just import and call

**Test Writer skill prompt:**
```
Use the test-writer skill for: backend/app/services/ranker.py
Target function: score_place, rank_places, internal helpers _weather_fit, _prompt_match, _proximity
No external HTTP calls. No database.
Generate parametrized tests covering:
  1. Weather scenarios (rainy, sunny, hot, neutral)
  2. Prompt matching (matching, non-matching, no preference)
  3. Proximity calculation (zero, horizon, midpoint, None)
  4. Rank diversity cap behaviour
  5. Edge cases (empty input, missing coords)
```

---

## Plan Phase (Tests Written First)

Test file structure written before implementation review:
```
TestWeatherFit
  - test_rainy_weather_prefers_indoor
  - test_sunny_weather_prefers_outdoor
  - test_hot_weather_prefers_indoor
  - test_unknown_weather_returns_neutral

TestPromptMatch
  - test_matching_category_scores_high
  - test_non_matching_category_scores_low
  - test_no_preference_returns_neutral
  - test_food_preference_matches_restaurant (adjusted for effective_pref semantics)
  - test_history_preference_matches_fort

TestProximity
  - test_zero_distance_is_one
  - test_horizon_distance_is_zero
  - test_none_distance_is_neutral
  - test_midpoint_is_half

TestRankPlaces
  - test_returns_max_results
  - test_places_have_score_field
  - test_diversity_cap_limits_same_category
  - test_places_without_coords_are_skipped
  - test_rainy_weather_ranks_indoor_higher
  - test_empty_places_returns_empty

TestScorePlace
  - test_score_is_between_zero_and_one
  - parametrized preference/category matrix (3 cases)
```

---

## Issue Discovered During TDD

**Test:** `test_food_preference_matches_restaurant`

First version tested: `_prompt_match(restaurant, "I want to eat something good")`

**Why it failed:** `_prompt_match` looks for bucket keys (e.g., "food") as substrings of the preference string. "I want to eat something good" contains "eat" but not "food". The bucket key "food" is not present → falls through to token overlap pass → score = 0.25, not ≥ 0.7.

**Why this is correct behavior:** In the actual pipeline, `trip_service` builds `effective_pref = "food peaceful I want to eat something good"` (category + mood + raw preference). So `_prompt_match` DOES see "food" in the effective preference — but only when called from the full pipeline.

**Fix to test:** Changed the test preference to `"food restaurants"` which directly contains the bucket key. This tests the ranker function's actual contract, not an implicit integration assumption.

**Lesson documented in retrospective:** AI-generated tests can embed incorrect assumptions about function contracts. Always trace through the code manually before asserting specific numeric bounds.

---

## Final Results

```
TestWeatherFit: 4/4 passed
TestPromptMatch: 5/5 passed
TestProximity: 4/4 passed
TestRankPlaces: 6/6 passed
TestScorePlace: 4/4 passed
Total: 23/23 passed
Coverage for ranker.py: 96%
```
