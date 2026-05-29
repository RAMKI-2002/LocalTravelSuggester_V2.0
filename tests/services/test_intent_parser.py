"""Unit tests for the intent parser service."""

from __future__ import annotations

import pytest

from backend.app.services.intent_parser import parse_intent_rule_based, normalise_llm_payload, VALID_CATEGORIES, VALID_MOODS


class TestParseIntentRuleBased:
    @pytest.mark.parametrize("prompt,expected_category", [
        ("I want to eat something good", "food"),
        ("hungry and want biryani", "food"),
        ("peaceful temple visit", "spiritual"),
        ("Birla Mandir", "spiritual"),
        ("history and forts", "history"),
        ("ancient heritage monument", "history"),
        ("shopping in malls", "shopping"),
        ("adventure trekking", "adventure"),
        ("fun with kids", "family"),
        ("romantic date night", "romantic"),
        ("art gallery visit", "art"),
        ("nightlife and clubs", "nightlife"),
        ("peaceful evening", "nature"),
        ("park and nature", "nature"),
        ("fun weekend", "family"),
        ("", "tourist"),
        (None, "tourist"),
    ])
    def test_category_from_prompt(self, prompt, expected_category):
        result = parse_intent_rule_based(prompt)
        assert result.category == expected_category

    def test_empty_prompt_returns_default(self):
        result = parse_intent_rule_based("")
        assert result.category == "tourist"
        assert result.source == "default"

    def test_none_prompt_returns_default(self):
        result = parse_intent_rule_based(None)
        assert result.category == "tourist"

    def test_rule_match_sets_source_to_rule(self):
        result = parse_intent_rule_based("want to eat food")
        assert result.source == "rule"

    def test_no_match_sets_source_to_default(self):
        result = parse_intent_rule_based("something completely random xyz")
        assert result.source == "default"
        assert result.category == "tourist"

    def test_search_keywords_are_returned(self):
        result = parse_intent_rule_based("food restaurant")
        assert isinstance(result.search_keywords, list)
        assert len(result.search_keywords) > 0

    def test_spiritual_prompt_has_peaceful_mood(self):
        result = parse_intent_rule_based("spiritual temple visit")
        assert result.mood == "peaceful"

    def test_adventure_prompt_has_energetic_mood(self):
        result = parse_intent_rule_based("adventure trekking")
        assert result.mood == "energetic"

    def test_query_string_joins_keywords(self):
        result = parse_intent_rule_based("food")
        assert result.query_string == " ".join(result.search_keywords)

    def test_partial_word_does_not_match(self):
        # "heart" should not match "art " (note trailing space in rule)
        result = parse_intent_rule_based("heartfelt journey")
        # Should not match "art" category
        assert result.category != "art"


class TestNormaliseLLMPayload:
    def test_valid_category_is_preserved(self):
        result = normalise_llm_payload({"category": "food", "search_keywords": ["restaurants"]}, "test")
        assert result.category == "food"
        assert result.source == "llm"

    def test_invalid_category_falls_back_to_tourist(self):
        result = normalise_llm_payload({"category": "invalid_xyz", "search_keywords": ["test"]}, "test")
        assert result.category == "tourist"

    def test_valid_mood_is_preserved(self):
        result = normalise_llm_payload({"category": "nature", "search_keywords": ["parks"], "mood": "peaceful"}, "test")
        assert result.mood == "peaceful"

    def test_invalid_mood_becomes_none(self):
        result = normalise_llm_payload({"category": "food", "search_keywords": ["restaurants"], "mood": "angry"}, "test")
        assert result.mood is None

    def test_missing_keywords_uses_defaults(self):
        result = normalise_llm_payload({"category": "food"}, "test")
        assert isinstance(result.search_keywords, list)
        assert len(result.search_keywords) > 0

    def test_keywords_capped_at_six(self):
        result = normalise_llm_payload({
            "category": "tourist",
            "search_keywords": ["a", "b", "c", "d", "e", "f", "g", "h"],
        }, "test")
        assert len(result.search_keywords) <= 6

    @pytest.mark.parametrize("cat", list(VALID_CATEGORIES))
    def test_all_valid_categories_are_accepted(self, cat):
        result = normalise_llm_payload({"category": cat, "search_keywords": ["test"]}, "")
        assert result.category == cat

    @pytest.mark.parametrize("mood", list(VALID_MOODS))
    def test_all_valid_moods_are_accepted(self, mood):
        result = normalise_llm_payload({"category": "tourist", "search_keywords": ["test"], "mood": mood}, "")
        assert result.mood == mood
