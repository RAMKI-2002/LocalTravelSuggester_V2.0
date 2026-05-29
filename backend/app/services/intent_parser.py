"""Intent extraction: free-text preference → structured TripIntent.

Strategy:
  1. Rule-based keyword matching (fast, deterministic, no LLM cost).
     Covers ~90% of common prompts ("food", "history", "peaceful").
  2. LLM fallback for ambiguous inputs ("want to eat", "feeling tired").
     Only invoked when rule-based returns the default "tourist" category.
  3. If LLM fails, the rule-based default is used.

The result feeds Foursquare's query parameter and the ranker's preference
matching — different intents genuinely produce different place pools.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.clients.llm_client import LLMClient

logger = logging.getLogger(__name__)

VALID_CATEGORIES: set[str] = {
    "food", "spiritual", "nature", "adventure", "history",
    "shopping", "family", "art", "romantic", "nightlife", "tourist",
}
VALID_MOODS: set[str] = {"peaceful", "fun", "energetic", "romantic", "social"}

_RULES: list[tuple[list[str], str, list[str], Optional[str]]] = [
    (["eat", "food", "hungry", "restaurant", "cafe", "dine", "lunch", "dinner",
      "breakfast", "snack", "cuisine", "tasty", "biryani", "street food", "drink", "bar", "pub"],
     "food", ["restaurants", "cafes", "food"], None),
    (["temple", "spiritual", "religious", "pray", "shrine", "mosque", "church",
      "monastery", "ashram", "meditation", "mandir", "masjid", "gurudwara"],
     "spiritual", ["temples", "religious places", "spiritual"], "peaceful"),
    (["history", "historic", "monument", "fort", "palace", "ancient", "heritage", "ruins", "museum"],
     "history", ["historic monuments", "forts", "museums"], None),
    (["shopping", "mall", "shop ", "buy ", "market", "souvenir", "bazaar", "boutique"],
     "shopping", ["malls", "markets", "shopping"], None),
    (["adventure", "trek", "hike", "thrill", "exciting", "rafting", "climb", "zip-line"],
     "adventure", ["adventure", "trekking", "hiking"], "energetic"),
    (["kids", "children", "child", "family", "toddler"],
     "family", ["family-friendly attractions", "parks", "zoos", "amusement parks"], "fun"),
    (["romantic", "date night", "couple", "anniversary", "honeymoon"],
     "romantic", ["romantic spots", "viewpoints", "gardens", "fine dining"], "romantic"),
    (["art ", "gallery", "exhibition", "artwork", "painting", "sculpture"],
     "art", ["art galleries", "art museums"], None),
    (["nightlife", "club", "rooftop", "lounge", "live music", "party"],
     "nightlife", ["nightlife", "rooftops", "clubs", "lounges"], "social"),
    (["peaceful", "calm", "quiet", "relax", "serene", "chill", "unwind", "tired"],
     "nature", ["parks", "gardens", "lakes", "viewpoints"], "peaceful"),
    (["nature", "outdoor", "park ", "garden", "lake", "scenic", "viewpoint", "hill", "waterfall", "beach"],
     "nature", ["parks", "gardens", "lakes", "viewpoints", "nature"], None),
    (["fun", "enjoy", "entertainment", "play", "weekend"],
     "family", ["amusement parks", "fun things to do"], "fun"),
]

_NON_WORD = re.compile(r"[^a-z0-9]+")


def _normalise_text(prompt: str) -> str:
    """Pad with spaces so partial-word matches don't bleed (e.g. "park " doesn't hit "Lumbini Park")."""
    return " " + _NON_WORD.sub(" ", prompt.lower()).strip() + " "


@dataclass
class TripIntent:
    raw_prompt: Optional[str]
    category: str = "tourist"
    search_keywords: list[str] = field(
        default_factory=lambda: ["tourist attractions", "things to do"]
    )
    mood: Optional[str] = None
    source: str = "default"

    @property
    def query_string(self) -> str:
        return " ".join(self.search_keywords)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_intent_rule_based(prompt: Optional[str]) -> TripIntent:
    """Deterministic keyword-based intent parser. No LLM cost."""
    if not prompt or not prompt.strip():
        return TripIntent(raw_prompt=prompt, source="default")

    haystack = _normalise_text(prompt)
    for keywords, category, search_kw, mood in _RULES:
        for kw in keywords:
            needle = kw if " " in kw else f" {kw} "
            if needle in haystack:
                return TripIntent(
                    raw_prompt=prompt,
                    category=category,
                    search_keywords=list(search_kw),
                    mood=mood,
                    source="rule",
                )

    return TripIntent(raw_prompt=prompt, source="default")


def normalise_llm_payload(payload: dict[str, Any], prompt: str) -> TripIntent:
    """Validate + coerce LLM JSON output to a safe TripIntent."""
    raw_cat = str(payload.get("category") or "").strip().lower()
    category = raw_cat if raw_cat in VALID_CATEGORIES else "tourist"

    raw_kw = payload.get("search_keywords") or payload.get("keywords") or []
    if isinstance(raw_kw, str):
        raw_kw = [raw_kw]
    keywords = [str(k).strip().lower() for k in raw_kw if isinstance(k, str) and str(k).strip()]
    if not keywords:
        keywords = _default_keywords(category)
    keywords = keywords[:6]

    raw_mood = payload.get("mood")
    mood = None
    if isinstance(raw_mood, str):
        m = raw_mood.strip().lower()
        mood = m if m in VALID_MOODS else None

    return TripIntent(raw_prompt=prompt, category=category, search_keywords=keywords, mood=mood, source="llm")


def _default_keywords(category: str) -> list[str]:
    return {
        "food": ["restaurants", "cafes", "food"],
        "spiritual": ["temples", "religious places"],
        "nature": ["parks", "gardens", "lakes", "viewpoints"],
        "adventure": ["adventure", "trekking", "hiking"],
        "history": ["historic monuments", "forts", "museums"],
        "shopping": ["malls", "markets", "shopping"],
        "family": ["family-friendly attractions", "amusement parks"],
        "art": ["art galleries", "art museums"],
        "romantic": ["romantic spots", "viewpoints", "fine dining"],
        "nightlife": ["nightlife", "rooftops", "clubs"],
    }.get(category, ["tourist attractions", "things to do"])


async def extract_intent(prompt: Optional[str], llm: "LLMClient") -> TripIntent:
    """Best-effort intent extraction: rule-based first, LLM escalation for ambiguous inputs."""
    rule_result = parse_intent_rule_based(prompt)

    if rule_result.category != "tourist" or not prompt:
        return rule_result

    try:
        payload = await llm.extract_intent(prompt)
    except Exception as exc:
        logger.warning("LLM extract_intent raised, using rule fallback: %s", exc)
        return rule_result

    if not payload:
        return rule_result

    try:
        return normalise_llm_payload(payload, prompt)
    except Exception as exc:
        logger.warning("LLM intent payload invalid (%s); using rule fallback", exc)
        return rule_result
