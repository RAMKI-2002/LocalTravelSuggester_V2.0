# /speckit.tasks — Task Breakdown

Use this command to generate implementation tasks from the plan.

## How to use

Invoke: `/speckit.tasks`

Reads `specs/[feature]/plan.md` and generates `specs/[feature]/tasks.md`.

## Output format per task

```markdown
## Task N: [Name]
Duration: [1-4 hours]
Depends on: [Task IDs]

### Implementation
- [What to build]

### Tests to Write First (TDD)
- test_[scenario]_[expected]: [assertion]

### Acceptance Criteria
- [ ] [testable criterion]
```

## Rules

- Each task: 1-4 hours maximum
- Tests listed BEFORE implementation notes
- Dependencies explicitly stated
- Identify independent tasks for parallel execution

## Reference

Constitution: `.specify/memory/constitution.md`
Existing tasks: `specs/local-travel-suggester/tasks.md`
