# Code Reviewer Subagent

## Purpose

Perform a systematic code review of a given file or module. This subagent reviews
against the project's specs, rules, and acceptance criteria — not just style.

## How to invoke

In Cursor Agent chat:
```
Review [file or module] for correctness, simplicity, and compliance with project rules.
```

Or after completing a task:
```
/requesting-code-review
Review backend/app/[module].py against:
- specs/local-travel-suggester/spec.md (acceptance criteria)
- .cursor/rules/project-rules.mdc (project conventions)
- .cursor/rules/fastapi-rules.mdc (FastAPI patterns)
Output findings to docs/code-review.md
```

## Review Dimensions

### 1. Correctness
- Does the implementation match the acceptance criteria in the spec?
- Are all edge cases handled (empty input, missing data, API failures)?
- Are error responses correct (status codes, message format)?

### 2. Simplicity
- Is there unnecessary abstraction (abstract classes where one class suffices)?
- Are there magic numbers or unexplained constants?
- Could this be shorter without losing clarity?

### 3. Security
- Are passwords ever returned in a response?
- Is user input validated before use?
- Are all protected endpoints using `get_current_user`?
- Is any secret hardcoded?

### 4. FastAPI conventions (`.cursor/rules/fastapi-rules.mdc`)
- Does every route have a `response_model`?
- Does every route use `Depends()` for DB and auth?
- Is business logic in the service layer, not the route?
- Are blocking calls (boto3) wrapped in `asyncio.to_thread()`?

### 5. Testability
- Can this be tested in isolation?
- Are external dependencies mockable?
- Are there hidden global state dependencies?

## Severity Scale

- **P1** — Must fix before any deployment (security, correctness bugs)
- **P2** — Should fix before team code review (convention violations, edge cases)
- **P3** — Informational / nice to have

## Output format

```markdown
### [filename]
**P[severity] — [short description]**
[Explanation of issue and suggested fix]
```

## Reference

- Project rules: `.cursor/rules/project-rules.mdc`
- FastAPI rules: `.cursor/rules/fastapi-rules.mdc`
- Testing rules: `.cursor/rules/testing-rules.mdc`
- Spec: `specs/local-travel-suggester/spec.md`
- Full review: `docs/code-review.md`
