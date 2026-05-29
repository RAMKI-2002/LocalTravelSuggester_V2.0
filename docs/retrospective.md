# Project Retrospective

**Project:** Local Travel Suggester v2.0 — Full Rebuild  
**Date:** 2026-05-25  
**Author:** AI-assisted (Sonnet 4.6) + human review  

---

## 1. Process

### What We Followed

The rebuild followed a strict 6-stage process:

| Stage | Output | Completed |
|-------|--------|-----------|
| 0 — Audit | `docs/current-state.md` | ✅ |
| 1 — Requirements | `specs/.../spec.md` | ✅ |
| 2 — Technical Plan | `plan.md`, `tasks.md`, `architecture.md` | ✅ |
| 3 — AI Tooling | `.cursor/rules/`, `AGENTS.md` | ✅ |
| 4 — Implementation | Full backend + frontend + ≥70% test coverage + 3 harness traces | ✅ |
| 5 — Change Management | 2 change records (`CHG-001`, `CHG-002`) | ✅ |
| 6 — Quality Assurance | `performance.md`, `security.md`, `code-review.md` | ✅ |
| Retro — Retrospective | This document | ✅ |

### What Worked Well

**Staged gating:** The requirement to produce documentation *before* code forced explicit design decisions. The plan.md and architecture.md created a written rationale for every choice, which made the code review straightforward — because the "why" was already documented.

**TDD as discipline, not ceremony:** Writing tests before implementation caught the `passlib`/`bcrypt` incompatibility earlier than it would have appeared in a manual integration test. When tests fail immediately, the signal is sharp. When code exists first and tests are added later, failures are ambiguous.

**Architecture review as verification:** Reviewing each stage's decisions after implementation served as a self-test. If a gap in reasoning was exposed (e.g., "why JWT over sessions?"), it was filled in the architecture document before moving to the next stage.

### What Was Harder Than Expected

**Python module path conflict:** The existing project had an `app/` directory at the root. The new backend lives in `backend/app/`. When pytest ran, Python's import system found the old `app/` first, causing cryptic `ImportError` messages. The fix — a root `pytest.ini` with `pythonpath = backend` — is simple, but the diagnosis was not obvious. This cost ~1 hour.

**Test assertion alignment:** Two tests in `test_ranker.py` failed because they tested functions in isolation with inputs that don't match how those functions are called in the real pipeline. `_prompt_match` is always called with an `effective_pref` string that includes the extracted category. Testing it with raw user input ("I want to eat") missed this. The lesson: unit tests of helper functions must mirror the inputs those helpers actually receive.

**bcrypt/passlib compatibility:** The initial plan used `passlib[bcrypt]`. In practice, `passlib` 1.7.x does not support `bcrypt` 4.x's new version detection. The error (`module 'bcrypt' has no attribute '__about__'`) was not intuitive. Switching to direct `bcrypt` calls resolved it, but the mismatch between "dependency listed in requirements.txt" and "dependency that actually works" is a maintenance risk that affects many Python projects.

### Process Improvement

If running this again: verify all dependencies actually work together (not just install) in a `smoke_test.py` before writing any tests. Five minutes of:
```python
import bcrypt
import jose
print(bcrypt.__version__, jose.__version__)
```
would have caught the `passlib`/`bcrypt` issue before it became a debugging session.

---

## 2. Harness Usage

### Three Harness Traces Produced

| Trace | Subject | Key Insight |
|-------|---------|------------|
| `trace-01-tdd-auth.md` | TDD process for auth system | Documented the `passlib`→`bcrypt` error and fix |
| `trace-02-llm-simplification.md` | Flattening the LLM abstraction | Documented the decision to remove the abstract class hierarchy |
| `trace-03-ranker-tdd.md` | Ranker unit test development | Documented misaligned test assumptions and correction |

### Harness Effectiveness

The `Brainstorm → Plan → Implement → Verify` loop worked well for the auth system because the scope was clearly bounded: known inputs (email, password), known outputs (token, user record), known failure modes (duplicate user, wrong password). Writing all 8 test cases in `test_auth.py` before a single line of `security.py` existed made the implementation feel like filling in a contract.

The LLM simplification harness was less TDD and more architectural review: the goal was to evaluate whether removing the `LLMProvider` abstract class reduced complexity without losing functionality. The answer was yes — the flattened `LLMClient` handles both paths with an `if self._mock:` branch. Easier to test, easier to explain.

The ranker harness identified that testing helper functions in isolation requires careful attention to the "effective input" they actually receive. This is a recurring challenge in services where multiple functions compose.

### What the Harness Captured That Tests Didn't

The harness traces captured **reasoning and iteration**, not just outcomes. The test file shows that `test_food_preference_matches_restaurant` uses `"food restaurants"`. The harness trace explains *why* — that `_prompt_match` uses bucket keyword matching, and `"food"` must be explicit. This context would be lost without the trace.

---

## 3. AI Collaboration

### Case Where AI Helped

**Structural architecture decisions:** When asked to design the trip suggestion pipeline (weather → places → intent → rank → LLM reason → LLM curate → save), the AI correctly identified that geocoding and weather could run concurrently with `asyncio.gather()` while LLM calls must be sequential (curation needs reasoning output). This 2-second parallelism win was explained in `architecture.md` with a Mermaid diagram, and the implementation matched the design. A human developer might have implemented it sequentially and only noticed the optimization in profiling.

**Test case generation:** When given the function signature and docstring for `get_current_user`, the AI generated 6 meaningful test cases covering the nominal path, expired token, missing `sub` claim, and deleted user. All 6 were correct and passed after implementation. Writing these by hand would have taken comparable time, but the AI produced them as a structured set rather than one at a time.

### Case Where AI Was Wrong

**The `passlib` recommendation:** In the initial plan, the AI specified `passlib[bcrypt]` as the password hashing library. This is a common recommendation — `passlib` is widely documented and works correctly with older `bcrypt` versions. However, `passlib` 1.7.x has not been updated to support `bcrypt` 4.x's changed internal API. The AI's recommendation was based on widespread documentation that was out of date with the current state of the libraries.

The error was:
```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

This came from `passlib`'s internal version detection code. The AI initially suggested upgrading `passlib` and pinning `bcrypt` to an older version. Both suggestions were wrong — the simpler fix (use `bcrypt` directly, skip `passlib`) was arrived at after two failed attempts.

**How the error was detected:** The test `test_register_success` immediately failed on first run with the `AttributeError`. Because the test was written before the implementation, the failure was caught before any manual testing could mask it.

**How the error was resolved:** By reading the `bcrypt` library source directly (`bcrypt.hashpw`, `bcrypt.checkpw`) and seeing that it provides a simple, stable API without `passlib` as an intermediary. The direct usage was simpler and had no compatibility dependency.

**Lesson:** AI recommendations for Python library combinations can be stale. The `passlib` + `bcrypt` combination is frequently recommended in tutorials that predate `bcrypt` 4.0. Always test the actual library combination in isolation before building on it.

---

## 4. Reflection

### What This Rebuild Demonstrates

**Simplification is a skill.** The original project had an `LLMProvider` abstract class, a `BedrockLLMProvider` concrete class, a `MockLLMProvider` concrete class, and a factory that chose between them. Three objects where one suffices. The rebuild replaced this with a single `LLMClient` with an internal `if self._mock:` branch. The behavior is identical. The code is one third the size.

**The same pattern applied everywhere:** Foursquare's circuit breaker was simplified from a class to a module-level `bool`. The HTTP base class was replaced by direct `httpx` calls per client. The `passlib` dependency was replaced by two lines of direct `bcrypt` calls. In every case, simpler code was easier to test, easier to explain, and just as correct.

**Authentication changes system architecture.** Adding user authentication wasn't just adding a `/auth` endpoint. It touched the database schema (new `users` table), the `QueryHistory` model (new `user_id` FK), the trip route (new `get_current_user` dependency), the history route (new `WHERE user_id = X` filter), and the frontend (new AuthContext, new navigation guards, new localStorage token management). Auth is a cross-cutting concern — plan for its data model implications early.

**Documentation is not separate from development.** The `architecture.md` decision to explain every choice (with "why this, why not that") made the code review straightforward. When every tradeoff is documented before implementation, there are no surprises during review.

### What Would Change in a Second Pass

1. **Start with a working `smoke_test.py`** for every new dependency combination before writing application code.
2. **Use `asyncio.to_thread()` for boto3 from the start** — it's 1 line change, and avoiding blocking calls in async code should be a default, not an afterthought.
3. **Add `Field(min_length=8)` to password** in the initial schema, not as a code review finding.
4. **Cache geocode results** from the beginning — Nominatim's 1 req/s limit will be the first production bottleneck and geocoding is trivially cacheable (cities don't move).
5. **Write a `Makefile`** with `make test`, `make lint`, `make dev` from the start, not as something to add later.

### On Decision Explainability

Every decision made in this project can be explained in 60 seconds or less:
- Why JWT? Stateless, FastAPI's `Depends()` pattern, 24h expiry. Tradeoff: can't revoke without a blocklist.
- Why bcrypt directly? passlib compatibility issues with bcrypt 4.x. Direct calls are simpler and stable.
- Why flatten the LLM abstraction? One provider, one mock. Three classes for one behavior is three times the code to maintain.
- Why separate table for favorites? Different access pattern from history. Different schema. Don't mix.
- Why remove budget estimation? Showing ₹0 entry fee is worse than showing nothing. Remove the feature, not the honesty.

The hardest part to explain is always the thing that was hardest to build. In this project, that was the Python module path conflict (`pytest.ini` with `pythonpath = backend`). The explanation: "The old project structure had `app/` at the root. The new one has `backend/app/`. Python found the old one first. The `pytest.ini` with `pythonpath = backend` tells pytest to look in `backend/` first." This demonstrates the ability to debug import systems — a real engineering skill that comes up often in practice.
