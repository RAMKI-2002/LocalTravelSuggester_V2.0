# AGENTS.md — LocalTravelSuggester

This file defines the AI collaboration conventions for this project.
Primary tool: **Cursor Agent Mode**.
Reference: `.cursor/rules/` for all coding, testing, and FastAPI rules.

---

## Agent Roles

### 1. Architect Agent
**Purpose:** Answer architectural questions about the system design.
**Prompt template:**
```
You are reviewing the LocalTravelSuggester backend.
Context: FastAPI + Python 3.11, SQLAlchemy 2.0, JWT auth, AWS Bedrock LLM.
Architecture rules: backend/app/ has api/, services/, clients/, db/, schemas/, core/ layers.
No business logic in routes. No HTTP in services.

Question: [your question]
```
**Used for:** "Should I put this logic in the service or the route?" "Is this the right place for this class?"

---

### 2. Test Writer Agent
**Purpose:** Generate pytest tests before implementation (TDD).
**Skill file:** `.cursor/skills/test-writer/SKILL.md`
**Prompt template:**
```
Using the test-writer skill:
Generate tests for [route or function name].
The route is in backend/app/api/[file].py.
It requires auth: [yes/no].
External calls it makes: [list].
```
**Used for:** Every new route or service function, before writing the implementation.

---

### 3. Code Reviewer Agent
**Purpose:** Review a code change for correctness, simplicity, and code quality.
**Prompt template:**
```
You are a senior Python engineer reviewing code for this project.
Project rules: see .cursor/rules/project-rules.mdc
Evaluate this code for:
1. Does it satisfy the requirement?
2. Is it simpler than the alternative? (flag any unnecessary abstractions)
3. Is the error handling correct?
4. Is it testable without modification?
5. Would a new developer understand it in under 5 minutes?

Code to review:
[paste code]
```
**Used for:** After each task is implemented, before marking it complete.

---

### 4. Debugger Agent
**Purpose:** Diagnose test failures and runtime errors.
**Prompt template:**
```
LocalTravelSuggester backend error.
Stack: FastAPI + SQLAlchemy 2.0 + pytest.
Test command: pytest tests/ -v
Error output:
[paste error]

Relevant files: [list changed files]
What is wrong and how do I fix it?
```
**Used for:** When `pytest` output shows a failure that isn't immediately obvious.

---

## Collaboration Conventions

### Brainstorm → Plan → Implement → Verify (for every task)

1. **Brainstorm:** Ask Cursor: "What are the ways I could implement [feature]?" Review options. Choose the simplest.
2. **Plan:** Write the test cases first (use Test Writer Agent). Commit test stubs.
3. **Implement:** Ask Cursor to implement against the failing tests. Review the generated code before accepting.
4. **Verify:** Run `pytest --cov=app`. If coverage < 70%, ask Debugger Agent why.

### When to Override AI Output
- If Cursor generates an abstract base class for a use case with one implementation: **reject it**. Ask for a simpler approach.
- If Cursor generates a new file for a class that is under 30 lines: **reject it**. Ask to inline it in the caller.
- If Cursor generates a generic factory or registry pattern: **reject it unless** the feature spec explicitly requires pluggable providers.
- If Cursor generates TypeScript for the frontend: **reject it**. The project uses plain JavaScript.

### Documentation Standard
- Every architectural decision must be explained as: "Why this? What alternative? Why rejected? What tradeoff?"
- Harness traces are stored in `docs/harness-traces/` for at least 3 representative tasks.
- The retrospective must include one AI error and how it was caught.

---

## File Ownership Map

| File/Folder | Owner (who modifies it) | Notes |
|-------------|------------------------|-------|
| `.cursor/rules/` | Human reviewer | Not modified by agents during implementation |
| `specs/` | Human + Architect Agent | Set before implementation begins |
| `backend/app/` | Code Agent (human-reviewed) | All changes reviewed before commit |
| `tests/` | Test Writer Agent | Written before implementation |
| `docs/` | All agents + human | Updated continuously |
| `frontend/src/` | Code Agent (human-reviewed) | React components |

---

## Prompts for Common Tasks

### Add a new API endpoint
```
Add a new FastAPI endpoint to backend/app/api/[file].py.
Follow .cursor/rules/fastapi-rules.mdc.
Endpoint: [METHOD] [path]
Request schema: [describe]
Response schema: [describe]
Auth required: [yes/no]
Business logic: call [service function] in services/[file].py
Write tests first in tests/test_[feature].py.
```

### Add a new database model
```
Add a new SQLAlchemy 2.0 ORM model to backend/app/db/models.py.
Use mapped_column() syntax (not the old Column() style).
Model name: [Name]
Columns: [list with types]
Relationships: [describe FK if any]
After adding the model, verify init_db() creates the table (run the app locally).
```

### Debug a failing test
```
This test is failing: [test name]
Error: [paste error]
Files involved: [list]
Use the Debugger Agent role.
Do not change the test — fix the implementation.
```
