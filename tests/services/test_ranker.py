"""Unit tests for the place ranker service."""

from __future__ import annotations

import pytest

from app.services.ranker import score_place, rank_places, _weather_fit, _prompt_match, _proximity


def _make_place(name: str, categories: list, lat: float = 17.4, lng: float = 78.5, rating: float = 7.0) -> dict:
    return {
        "name": name,
        "categories": categories,
        "coords": {"lat": lat, "lng": lng},
        "rating": rating,
        "popularity": None,
        "description": "",
        "_distance_km": 5.0,
    }


# ---------------------------------------------------------------------------
# weather_fit
# ---------------------------------------------------------------------------
class TestWeatherFit:
    def test_rainy_weather_prefers_indoor(self):
        indoor = _make_place("Museum", ["Museum"])
        outdoor = _make_place("Park", ["Park"])
        rainy = {"condition": "Rain", "temp_c": 24}
        assert _weather_fit(indoor, rainy) > _weather_fit(outdoor, rainy)

    def test_sunny_weather_prefers_outdoor(self):
        indoor = _make_place("Mall", ["Mall"])
        outdoor = _make_place("Lake", ["Lake"])
        sunny = {"condition": "Clear", "temp_c": 28}
        assert _weather_fit(outdoor, sunny) > _weather_fit(indoor, sunny)

    def test_hot_weather_prefers_indoor(self):
        indoor = _make_place("Aquarium", ["Aquarium"])
        outdoor = _make_place("Fort", ["Fort"])
        hot = {"condition": "Clear", "temp_c": 40}
        assert _weather_fit(indoor, hot) > _weather_fit(outdoor, hot)

    def test_unknown_weather_returns_neutral(self):
        place = _make_place("Something", ["Something Else"])
        unknown = {"condition": "Fog", "temp_c": 20}
        result = _weather_fit(place, unknown)
        assert 0.5 <= result <= 0.9  # neutral range


# ---------------------------------------------------------------------------
# prompt_match
# ---------------------------------------------------------------------------
class TestPromptMatch:
    def test_matching_category_scores_high(self):
        temple = _make_place("Birla Mandir", ["Temple", "Place of Worship"])
        score = _prompt_match(temple, "spiritual evening")
        assert score >= 0.8

    def test_non_matching_category_scores_low(self):
        restaurant = _make_place("KFC", ["Restaurant", "Fast Food"])
        score = _prompt_match(restaurant, "spiritual evening")
        assert score <= 0.2

    def test_no_preference_returns_neutral(self):
        place = _make_place("Anything", ["Attraction"])
        score = _prompt_match(place, None)
        assert score == 0.5

    def test_food_preference_matches_restaurant(self):
        restaurant = _make_place("Irani Cafe", ["Cafe", "Restaurant"])
        # Use "food" directly since _prompt_match matches bucket keys in the preference text.
        # The trip service passes "category + mood + raw_preference" as effective_pref.
        score = _prompt_match(restaurant, "food restaurants")
        assert score >= 0.7

    def test_history_preference_matches_fort(self):
        fort = _make_place("Golconda Fort", ["Fort", "Historic Monument"])
        score = _prompt_match(fort, "history and heritage")
        assert score >= 0.8


# ---------------------------------------------------------------------------
# proximity
# ---------------------------------------------------------------------------
class TestProximity:
    def test_zero_distance_is_one(self):
        assert _proximity(0.0) == 1.0

    def test_horizon_distance_is_zero(self):
        assert _proximity(25.0) == 0.0

    def test_none_distance_is_neutral(self):
        assert _proximity(None) == 0.6

    def test_midpoint_is_half(self):
        result = _proximity(12.5)
        assert abs(result - 0.5) < 0.01


# ---------------------------------------------------------------------------
# rank_places
# ---------------------------------------------------------------------------
class TestRankPlaces:
    def test_returns_max_results(self):
        places = [_make_place(f"Place {i}", ["Attraction"]) for i in range(10)]
        result = rank_places(places, {"condition": "Clear", "temp_c": 28}, None, 5)
        assert len(result) <= 5

    def test_places_have_score_field(self):
        places = [_make_place("Museum A", ["Museum"]), _make_place("Park B", ["Park"])]
        result = rank_places(places, {}, None, 5)
        for p in result:
            assert "_score" in p
            assert 0.0 <= p["_score"] <= 1.0

    def test_diversity_cap_limits_same_category(self):
        """Diversity cap limits same-category items in the primary pass.
        The cap allows top-up from leftovers when there are not enough diverse places,
        so the final count may exceed max_per_category when alternatives are exhausted.
        What matters: the cap causes diverse places to appear before pure-category overflow.
        """
        museums = [_make_place(f"Museum {i}", ["Museum"], rating=9.0) for i in range(4)]
        parks = [_make_place(f"Park {i}", ["Park"], rating=7.0) for i in range(4)]
        # With enough diverse places, museums should be limited to max_per_category
        result = rank_places(museums + parks, {}, None, 4, max_per_category=2)
        museum_count = sum(1 for p in result if "Museum" in (p.get("categories") or [""])[0])
        park_count = sum(1 for p in result if "Park" in (p.get("categories") or [""])[0])
        # Both categories should appear (diversity worked)
        assert museum_count <= 2
        assert park_count >= 1

    def test_places_without_coords_are_skipped(self):
        no_coords = {"name": "Ghost", "categories": ["Attraction"], "coords": {}}
        with_coords = _make_place("Real Place", ["Attraction"])
        result = rank_places([no_coords, with_coords], {}, None, 5)
        assert all("coords" in p and p["coords"].get("lat") is not None for p in result)

    def test_rainy_weather_ranks_indoor_higher(self):
        museum = _make_place("Museum", ["Museum"])
        park = _make_place("Park", ["Park", "outdoor"])
        rainy = {"condition": "Rain", "temp_c": 24}
        result = rank_places([museum, park], rainy, None, 2)
        # Museum should be ranked first in rainy weather
        assert result[0]["name"] == "Museum"

    def test_empty_places_returns_empty(self):
        result = rank_places([], {}, None, 5)
        assert result == []


# ---------------------------------------------------------------------------
# score_place
# ---------------------------------------------------------------------------
class TestScorePlace:
    def test_score_is_between_zero_and_one(self):
        place = _make_place("Test Place", ["Museum"])
        weather = {"condition": "Clear", "temp_c": 25}
        score = score_place(place, weather, "history")
        assert 0.0 <= score <= 1.0

    @pytest.mark.parametrize("preference,category,expected_high", [
        ("food and restaurants", ["Restaurant", "Cafe"], True),
        ("spiritual temple", ["Temple", "Place of Worship"], True),
        ("adventure trekking", ["Museum"], False),
    ])
    def test_preference_match_affects_score(self, preference, category, expected_high):
        place = _make_place("Test", category)
        weather = {"condition": "Clear", "temp_c": 25}
        score = score_place(place, weather, preference)
        if expected_high:
            assert score >= 0.5
        else:
            assert score <= 0.5
