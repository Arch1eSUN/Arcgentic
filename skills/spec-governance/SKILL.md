---
name: spec-governance
description: Use when a round uses proposal/design/tasks/spec/archive artifacts or needs OpenSpec-style artifact validation without depending on the OpenSpec CLI.
---

# spec-governance

Validates OpenSpec-style change artifacts as inputs to arcgentic planning, development,
and audit.

## Workflow

1. Check that the change directory has `proposal.md`, `design.md`, `tasks.md`, and
   `specs/**/*.md`.
2. Count complete and incomplete tasks.
3. Validate archive readiness without moving files:

   ```bash
   arcgentic spec-governance status openspec/changes/<change>
   arcgentic spec-governance validate openspec/changes/<change>
   arcgentic spec-governance archive openspec/changes/<change>
   ```

4. Map proposal/design/tasks/spec facts into handoff and audit facts.

## Boundaries

- V1 archive is validate-only.
- Do not add an OpenSpec npm dependency.
- Do not replace arcgentic's state machine with OpenSpec states.
