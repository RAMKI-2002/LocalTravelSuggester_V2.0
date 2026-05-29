# Harness Trace 02 — LLM Client Simplification

**Task:** C-01 Flatten LLM abstraction
**Date:** 2026-05-25
**Agent Role:** Architect → Code Reviewer

---

## Brainstorm Phase

**Problem identified in audit:**
The original `llm_client.py` had:
1. `LLMProvider` — abstract base class with 3 abstract methods
2. `BedrockLLMProvider(LLMProvider)` — concrete implementation (~100 lines)
3. `MockLLMProvider(LLMProvider)` — test stand-in (~50 lines)
4. `get_llm_provider()` — factory function with global singleton cache
5. `reset_llm_provider()` — test cleanup function

Total: 5 objects, 475 lines, for 1 real provider and 1 mock.

**Architect Agent prompt:**
```
The original llm_client.py uses an abstract base class + two subclasses + a factory.
This is for one real provider (Bedrock) and one mock.
Project rule: no abstractions without immediate, concrete benefit.
What is the simplest implementation that has the same behavior?
```

**AI response:**
"A single `LLMClient` class with `self._mock: bool` flag. Mock behaviour is implemented as branches inside each method (`if self._mock: return self._mock_xxx(...)`). No inheritance needed. Same singleton pattern with `get_llm_client()` / `reset_llm_client()`. ~200 lines vs 475 lines."

---

## Implementation Decision

**Accepted:** Single-class approach.

**Tradeoff acknowledged:**
- If a second real provider (e.g., OpenAI) is added later, refactoring is needed. This is an acceptable risk for a demo project — "You Aren't Gonna Need It."
- The abstract base class was defensive engineering for a hypothetical future requirement that doesn't exist.

---

## Code Review

**Reviewer prompt:**
```
Review backend/app/clients/llm_client.py.
Question: is this simpler than the original? Would a new developer understand it in 5 minutes?
Check: does it still support LLM_MOCK=true, Bedrock Converse API, curate/intent/reasoning?
```

**Review findings:**
- ✓ `_mock: bool` flag is self-documenting — easier to understand than inheritance hierarchy
- ✓ All 3 LLM use cases preserved
- ✓ Mock logic is co-located with real logic (no file-hopping to understand behavior)
- ✓ `get_llm_client()` / `reset_llm_client()` maintained for test isolation
- △ The `_invoke_sync` method is only called from real-Bedrock branches — clearly named

**Line count comparison:**
- Original: 477 lines across LLMProvider + BedrockLLMProvider + MockLLMProvider + factory
- New: 256 lines in a single file

---

## Verify Phase

Tests covering LLM client (via mocked mode):
```bash
python -m pytest tests/test_trip.py -v
```

All trip tests pass with `LLM_MOCK=true`. The mock branches exercise `generate_place_reasoning`, `curate_places`, and `extract_intent` paths.

**Coverage for llm_client.py:** 38% (only mock branches covered; Bedrock branches require real AWS creds — documented as expected gap)
