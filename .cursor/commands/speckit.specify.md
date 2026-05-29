# /speckit.specify — Requirements Definition

Use this command to define WHAT and WHY for a feature. No tech choices, no implementation details.

## How to use

Invoke: `/speckit.specify`

Then provide:
```
Feature: [Feature Name]
Target users: [who benefits]
Problem: [what problem this solves]
Stories:
  - As a [user] I can [action]
Out of scope: [explicit exclusions]
Non-functional: [performance, security, coverage requirements]
```

## Output

Creates or updates `specs/[feature]/spec.md` with:
- User stories
- Acceptance criteria (testable, not vague)
- Scope boundaries
- Non-functional requirements (quantified)

## Rules

- This stage answers WHAT and WHY only
- No stack choices in this document
- All acceptance criteria must be testable
- Review and trim AI-generated scope inflation before moving to /speckit.plan

## Reference

Constitution: `.specify/memory/constitution.md`
Existing specs: `specs/local-travel-suggester/spec.md`
