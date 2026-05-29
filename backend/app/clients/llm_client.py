"""LLM client — AWS Bedrock (Nova Lite) with rule-based mock fallback.

Simplification vs original:
  The original used an abstract LLMProvider base class with BedrockLLMProvider
  and MockLLMProvider subclasses plus a factory function. That is 4 objects for
  one real provider plus a mock.

  This version is a single LLMClient class. Mock behaviour is a branch inside
  each method controlled by self._mock (set from LLM_MOCK env var). Fewer
  files, same behaviour, easier to explain.

LLM usage in this project:
  1. extract_intent  — free-text preference → {category, keywords, mood}
  2. curate_places   — pick best N from top 2N rule-ranked shortlist (ONE call)
  3. generate_place_reasoning — per-place one-liner (only if curate didn't supply)

Safety: the LLM never invents places. curate_places validates every returned
name against the input list. Hallucinated names are silently dropped.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_REASONING = (
    "You are a helpful local trip-suggestion assistant. Given current weather, "
    "the user's preference, and a specific place, write ONE or TWO concise "
    "sentences (max 45 words) explaining why this place is a good fit right now. "
    "Mention the weather context naturally. Do not invent facts. Output plain text."
)

_SYSTEM_CURATE = (
    "You are a local trip-suggestion assistant. Pick the BEST matches for the "
    "user's preference from the candidate list. Hard rules: only use names from "
    "the list (never invent), prefer nearer places when distance is provided. "
    "Output STRICT JSON only: "
    '{"picks":[{"name":"<exact-name>","reason":"<one sentence <=35 words>"}]}'
)

_SYSTEM_INTENT = (
    "Translate a user trip preference into structured intent. "
    "Output STRICT JSON ONLY (no markdown):\n"
    '{"category":"<one of: food,spiritual,nature,adventure,history,shopping,family,art,romantic,nightlife,tourist>","search_keywords":["2-5 short keywords"],"mood":"<peaceful|fun|energetic|romantic|social|null>"}\n'
    "Rules: unclear/empty -> category=tourist, keywords=[tourist attractions]."
)


def _try_parse_json(raw: str) -> Optional[dict[str, Any]]:
    """Best-effort JSON extractor — handles fenced blocks and inline JSON."""
    raw = raw.strip()
    attempts = [raw]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        attempts.append(fenced.group(1))
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        attempts.append(brace.group(0))
    for attempt in attempts:
        try:
            obj = json.loads(attempt)
            if isinstance(obj, dict):
                return obj
        except (ValueError, TypeError):
            continue
    return None


class LLMClient:
    """Single LLM client class — real Bedrock when LLM_MOCK=false, rule-based mock otherwise."""

    def __init__(self) -> None:
        settings = get_settings()
        self._mock = settings.llm_mock
        self._model_id = settings.bedrock_model_id

        if not self._mock:
            try:
                import boto3
                client_kwargs: dict[str, Any] = {"region_name": settings.aws_region}
                if settings.aws_access_key_id and settings.aws_secret_access_key:
                    client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
                    client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
                self._bedrock = boto3.client("bedrock-runtime", **client_kwargs)
                logger.info("LLMClient: using Bedrock model %s", self._model_id)
            except Exception as exc:
                logger.warning("Bedrock init failed (%s) — falling back to mock", exc)
                self._mock = True

        if self._mock:
            logger.info("LLMClient: using rule-based mock (LLM_MOCK=true or Bedrock unavailable)")

    def _invoke_sync(
        self,
        user_prompt: str,
        *,
        system_prompt: str = _SYSTEM_REASONING,
        max_tokens: int = 180,
        temperature: float = 0.4,
    ) -> str:
        """Synchronous Bedrock call — run via asyncio.to_thread to avoid blocking the event loop."""
        response = self._bedrock.converse(
            modelId=self._model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature, "topP": 0.9},
        )
        content = response["output"]["message"]["content"]
        if not content:
            raise RuntimeError("Bedrock returned empty content")
        return content[0].get("text", "").strip()

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------
    async def generate_place_reasoning(
        self,
        weather: dict[str, Any],
        preference: Optional[str],
        place: dict[str, Any],
    ) -> str:
        if self._mock:
            return self._mock_reasoning(weather, preference, place)

        user_prompt = (
            f"Weather: {weather.get('condition')} at {weather.get('temp_c')}C "
            f"({weather.get('description') or 'n/a'}).\n"
            f"User preference: {preference or 'No specific preference'}.\n"
            f"Place: {place.get('name')} "
            f"(categories: {', '.join(place.get('categories') or []) or 'n/a'}).\n"
            f"Place description: {place.get('description') or 'n/a'}.\n"
            "Write the recommendation sentence now."
        )
        return await asyncio.to_thread(self._invoke_sync, user_prompt)

    async def curate_places(
        self,
        weather: dict[str, Any],
        preference: Optional[str],
        locality: Optional[str],
        candidates: list[dict[str, Any]],
        max_results: int,
    ) -> Optional[list[dict[str, Any]]]:
        if self._mock:
            return await self._mock_curate(weather, preference, candidates, max_results)

        if not candidates:
            return []

        lines = [
            f"Weather: {weather.get('condition')} at {weather.get('temp_c')}C.",
            f"User preference: {preference or 'No specific preference'}.",
            f"User locality: {locality or 'not provided'}.",
            f"Pick at most {max_results} matches.", "",
            "Candidates:",
        ]
        for idx, c in enumerate(candidates, 1):
            cats = ", ".join(c.get("categories") or []) or "n/a"
            dist = c.get("_distance_km")
            dist_str = f"{dist:.1f}km" if isinstance(dist, (int, float)) else "unknown"
            desc = (c.get("description") or "")[:120]
            lines.append(f"  {idx}. {c.get('name')} | cats: {cats} | dist: {dist_str}" + (f" - {desc}" if desc else ""))
        lines.append("\nReturn JSON in the schema given. Use exact names. Order by best fit first.")
        user_prompt = "\n".join(lines)

        try:
            raw = await asyncio.to_thread(
                self._invoke_sync, user_prompt,
                system_prompt=_SYSTEM_CURATE, max_tokens=600, temperature=0.3,
            )
        except Exception as exc:
            logger.warning("LLM curate call failed: %s", exc)
            return None

        obj = _try_parse_json(raw)
        if not obj or not isinstance(obj.get("picks"), list):
            logger.warning("LLM curate returned non-JSON (first 200): %r", raw[:200])
            return None

        by_name = {(c.get("name") or "").strip().lower(): c for c in candidates}
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pick in obj["picks"]:
            key = (pick.get("name") or "").strip().lower()
            if key in seen or key not in by_name:
                continue
            seen.add(key)
            enriched = dict(by_name[key])
            if pick.get("reason"):
                enriched["_reasoning"] = pick["reason"]
            out.append(enriched)
            if len(out) >= max_results:
                break

        return out or None

    async def extract_intent(self, prompt: str) -> Optional[dict[str, Any]]:
        if self._mock or not prompt.strip():
            return None  # orchestrator falls back to rule-based

        user_prompt = f'User prompt: "{prompt.strip()}"'
        try:
            raw = await asyncio.to_thread(
                self._invoke_sync, user_prompt,
                system_prompt=_SYSTEM_INTENT, max_tokens=200, temperature=0.1,
            )
        except Exception as exc:
            logger.warning("LLM extract_intent failed: %s", exc)
            return None

        return _try_parse_json(raw)

    # ---------------------------------------------------------------------------
    # Mock helpers (deterministic, offline)
    # ---------------------------------------------------------------------------
    def _mock_reasoning(
        self, weather: dict[str, Any], preference: Optional[str], place: dict[str, Any]
    ) -> str:
        cond = (weather.get("condition") or "").lower()
        temp = weather.get("temp_c")
        name = place.get("name", "This place")
        cats = ", ".join(place.get("categories") or []) or "local attraction"
        if "rain" in cond or "storm" in cond:
            suggestion = "an indoor-friendly pick that shields you from the weather"
        elif isinstance(temp, (int, float)) and temp >= 35:
            suggestion = "best visited in the early morning or late evening"
        elif "clear" in cond or "sun" in cond:
            suggestion = "great for an outdoor experience"
        else:
            suggestion = "a solid pick right now"
        pref_phrase = f" for your '{preference}' preference" if preference else ""
        return f"{name} ({cats}) is {suggestion}{pref_phrase}."

    async def _mock_curate(
        self,
        weather: dict[str, Any],
        preference: Optional[str],
        candidates: list[dict[str, Any]],
        max_results: int,
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []
        out = []
        for c in candidates[:max_results]:
            enriched = dict(c)
            enriched["_reasoning"] = self._mock_reasoning(weather, preference, c)
            out.append(enriched)
        return out


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm_client() -> None:
    """Clear the cached client — used in tests to ensure fresh state."""
    global _client
    _client = None
