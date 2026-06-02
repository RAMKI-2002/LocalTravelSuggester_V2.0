# AI-Assisted Development Workflow — LocalTravelSuggester

This document explains how AI tools were used to build this project, why each tool was chosen, and how to use the same workflow when extending or maintaining the project.

---

## Overview

This project was built using an AI-assisted development lifecycle — not by asking an AI to "write the app", but by using AI as a structured collaborator at each stage of the engineering process.

The core idea: **AI is most useful when it has context, constraints, and a clearly defined role.** The tools below exist to give AI that context.

```
Requirements
    ↓
Spec (WHAT + WHY)
    ↓
Technical Plan + Tasks (HOW)
    ↓
AI Rules (HOW TO CODE)
    ↓
TDD Implementation (WRITE + VERIFY)
    ↓
Change Records (MODIFY SAFELY)
    ↓
QA Review (VALIDATE)
```

---

## Tools Used in This Project

### 1. Cursor (AI-Powered IDE)

**What it is:** The IDE used to write all code. Cursor's Agent Mode can read files, run commands, and propose changes based on project context.

**How we used it:**
- Cursor Agent Mode ran each stage of the 6-stage engineering process
- Rules files (`.cursor/rules/`) gave the agent project-specific constraints
- Skills files (`.cursor/skills/`) gave the agent repeatable task templates
- The agent read specs before writing code — never the other way around

**Key principle:** Cursor is most useful when given a clear task with documented context. Open-ended prompts like "build the app" produce inconsistent results. Stage-gated prompts like "implement the auth service against these failing tests, following `fastapi-rules.mdc`" produce reliable results.

---

### 2. Cursor Rules (`.cursor/rules/`)

**What it is:** Markdown files that Cursor reads automatically when working in this project. They define coding standards, architecture rules, and patterns the AI must follow.

**Files in this project:**

| File | Purpose |
|------|---------|
| `.cursor/rules/project-rules.mdc` | General standards: naming, error handling, logging, complexity limits |
| `.cursor/rules/fastapi-rules.mdc` | FastAPI-specific patterns: route shape, dependency injection, response models |
| `.cursor/rules/testing-rules.mdc` | TDD rules: test-first, fixture patterns, mocking strategy |

**How to use them:**
- These files are applied automatically when Cursor is in agent mode
- When adding a new feature, update the relevant rule file if a new pattern is established
- Rules prevent AI from re-introducing complexity that was deliberately removed (e.g., abstract base classes, unnecessary factories)

**Example rule that saved significant rework:**
```
Do NOT create abstract base classes for single-implementation use cases.
If there is one provider and one mock, use a single class with an if-statement.
```
This rule stopped Cursor from recreating the over-engineered `LLMProvider → BedrockLLMProvider → MockLLMProvider` hierarchy from the original project.

---

### 3. Cursor Skills (`.cursor/skills/`)

**What it is:** Reusable prompt templates for specific tasks. A skill is a markdown file with a structured prompt that an agent can execute repeatedly.

**Skills in this project:**

| Skill | File | What it does |
|-------|------|-------------|
| Test Writer | `.cursor/skills/test-writer/SKILL.md` | Generates pytest tests before implementation (TDD harness) |

**How to use it:**
```
Using the test-writer skill:
Generate tests for [route or function name].
The route is in backend/app/api/[file].py.
It requires auth: [yes/no].
External calls it makes: [weather_client, places_client].
```

**Why skills matter:** Without a skill, asking "write tests for this route" produces different-quality results every time. With a skill, the prompt includes the fixture pattern, mocking strategy, and assertion style — so every test file follows the same structure.

---

### 4. GitHub Spec Kit (`specify`)

**What it is:** A CLI tool that helps generate structured specs and technical plans from requirements.

**How we used it:**
- `specify` was used as a reference workflow to produce `specs/local-travel-suggester/spec.md` and `plan.md`
- The `.specify/memory/constitution.md` file defines the project's governing principles (what it is, what it is not, what must always be true)
- The `.specify/templates/spec.md` file provides the template for future specs

**How to use it for a new feature:**
```bash
# Install (from GitHub, not PyPI):
uv tool install git+https://github.com/speckai/spec-kit.git

# On Windows, set encoding first:
$env:PYTHONIOENCODING = "utf-8"

# Then use Cursor's slash commands:
# /speckit.specify  → generates a spec
# /speckit.plan     → generates a technical plan
# /speckit.tasks    → generates a task breakdown
```

The Cursor slash commands for these are in `.cursor/commands/`.

---

### 5. OpenSpec (`openspec`)

**What it is:** A spec-driven change workflow. Each change produces proposal, design, capability specs, and tasks artifacts before code is written. Completed changes are archived and their specs promoted to `openspec/specs/`.

**How we used it:**
- **`remove-budget-estimation`** — removed per-place budget from API, UI, and place clients (archived at `openspec/changes/archive/2026-06-02-remove-budget-estimation/`)
- Main spec promoted: `openspec/specs/trip-suggestion/spec.md`

**How to create a change for a new feature:**
```bash
# Install (if not already):
npm install -g @openspec/cli

# Create a new change (spec-driven schema):
openspec new change "<kebab-case-name>"

# Generate artifacts in order: proposal → design → specs → tasks
openspec status --change "<name>" --json

# Implement against tasks.md, then archive (syncs specs to main):
openspec archive <name> -y
```

Each active change lives in `openspec/changes/<name>/` with:
- `proposal.md` — what and why
- `design.md` — how (technical decisions)
- `specs/<capability>/spec.md` — requirement deltas
- `tasks.md` — implementation checklist

**Why this matters:** Without structured change records, API modifications accumulate silently. The archived `remove-budget-estimation` change is the audit trail for removing `estimated_budget` from the trip suggestion contract.

---

## The 6-Stage Process This Project Followed

Each stage has a deliverable. Nothing moves forward until the deliverable exists.

| Stage | Name | Key Deliverable | Location |
|-------|------|----------------|----------|
| 0 | Audit | What exists, what's broken | `docs/current-state.md` |
| 1 | Requirements | What the system must do (WHAT/WHY, not HOW) | `specs/local-travel-suggester/spec.md` |
| 2 | Technical Plan | Architecture, API contracts, task breakdown | `specs/local-travel-suggester/plan.md`, `tasks.md`, `docs/architecture.md` |
| 3 | AI Tooling | Rules, skills, agent roles | `.cursor/rules/`, `.cursor/skills/`, `AGENTS.md` |
| 4 | Implementation | TDD — tests first, then code, ≥70% coverage | `backend/`, `frontend/`, `tests/`, `docs/harness-traces/` |
| 5 | Change Management | OpenSpec spec-driven changes (archived: `remove-budget-estimation`) | `openspec/changes/archive/`, `openspec/specs/` |
| 6 | Quality Assurance | Performance, security, code review | `docs/performance.md`, `docs/security.md`, `docs/code-review.md` |

---

## How to Add a New Feature (Using This Workflow)

If someone wants to add a new feature — say, "allow users to save favourite places" — here is the exact workflow:

### Step 1 — Write a spec first
Open `specs/local-travel-suggester/spec.md` or create `specs/favorites/spec.md`. Answer:
- Who uses it?
- What does it do?
- What are the acceptance criteria?
- What is OUT of scope?

Do not touch code yet.

### Step 2 — Propose an OpenSpec change
```bash
# In the project root:
openspec new change "<feature-name>"
```
Fill in `proposal.md`, `design.md`, `specs/<capability>/spec.md`, and `tasks.md` under `openspec/changes/<feature-name>/`.

### Step 3 — Write tests first (TDD)
Use the test-writer skill:
```
Using the test-writer skill:
Generate tests for POST /favorites and GET /favorites.
Auth required: yes.
External calls: none (database only).
```
Run the tests — they must fail before any implementation exists.

### Step 4 — Implement against the failing tests
Ask Cursor:
```
Implement the favorites feature.
Follow .cursor/rules/fastapi-rules.mdc and project-rules.mdc.
Make these tests pass: [list test names].
Do not add abstractions not required by the tests.
```
Review all generated code before accepting.

### Step 5 — Verify
```bash
pytest --cov=app --cov-report=term-missing
```
Coverage must stay ≥70%. All tests must pass.

### Step 6 — Update docs and archive
- Add the new endpoint to `docs/architecture.md`
- Mark tasks complete in `openspec/changes/<feature-name>/tasks.md`
- Archive the change: `openspec archive <feature-name> -y`
- Update `README.md` API reference table if endpoints changed

---

## TDD Harness Traces

`docs/harness-traces/` contains records of how specific features were test-driven. These are written traces — not code — that capture the decisions made during each TDD session.

| Trace | What it covers |
|-------|---------------|
| `auth-tdd.md` | How JWT, bcrypt, and get_current_user were test-driven |
| `llm-client-tdd.md` | How the LLM client mock was verified without AWS |
| `ranker-tdd.md` | How the weighted scoring function was verified with unit tests |

Read these before modifying the auth or ranking logic — they explain decisions that are not obvious from the code alone.

---

## What AI Helped With (And What It Got Wrong)

### Where AI was most useful

- **Test generation:** Given a function signature and docstring, Cursor generated 6 meaningful test cases for `get_current_user` covering the nominal path, expired token, missing claim, and deleted user — all correct on first generation.
- **Boilerplate elimination:** Generating repetitive but correct code (Pydantic schemas, SQLAlchemy models, FastAPI route stubs) with consistent style.
- **Documentation drafts:** `docs/architecture.md`, `docs/security.md`, and `docs/performance.md` were AI-drafted from the implementation, then human-reviewed and corrected.

### Where AI was wrong (and how it was caught)

- **Over-abstraction:** Cursor initially proposed `LLMProvider → BedrockLLMProvider → MockLLMProvider → factory get_llm_provider()` — 4 layers for one provider with a mock flag. Caught by the rule in `project-rules.mdc` that explicitly forbids this pattern. The fix: a single `LLMClient` class with `if self.mock_mode`.
- **Test input mismatch:** Two ranker tests failed because Cursor tested `_prompt_match()` with raw user input ("I want to eat") instead of the `effective_pref` string that the pipeline actually passes to it. Caught by running pytest and reading the failure output carefully. The fix: update the test inputs to match the real call site.

---

## Summary: Why This Workflow Produces Better Code

| Without this workflow | With this workflow |
|----------------------|-------------------|
| AI generates code based on the prompt alone | AI generates code with documented constraints (rules), templates (skills), and prior decisions (specs) |
| Changes are made directly to code | Changes go through proposal → spec diff → impact analysis → tasks |
| Tests are added after code (if at all) | Tests are written first; code exists to make them pass |
| Decisions are implicit in the code | Decisions are documented in `docs/architecture.md` before the code is written |
| New team members read code to understand intent | New team members read specs and architecture docs, then the code |

The code in this project is not particularly complex. The value is in the documented reasoning — any engineer joining the project can read `docs/architecture.md` and understand not just what the system does but why every major decision was made.
