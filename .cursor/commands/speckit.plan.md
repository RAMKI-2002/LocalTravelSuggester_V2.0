# /speckit.plan — Technical Plan

Use this command to define HOW — stack, architecture, data model, API design.

## How to use

Invoke: `/speckit.plan`

Then provide:
```
Stack: [tech choices with rationale]
Architecture: [layered design]
Reference spec: specs/[feature]/spec.md
```

## Output

Creates `specs/[feature]/plan.md` with:
- Stack decisions with tradeoff analysis
- Data model (tables, columns, relationships)
- API contracts (endpoints, request/response schemas)
- Folder structure
- Testing plan

## Rules

- Every architecture decision must include: why chosen, alternatives rejected, tradeoff
- The plan feeds directly into /speckit.tasks
- Validate with /writing-plans (Superpowers) before generating tasks

## Reference

Constitution: `.specify/memory/constitution.md`
Existing plan: `specs/local-travel-suggester/plan.md`
Architecture: `docs/architecture.md`
