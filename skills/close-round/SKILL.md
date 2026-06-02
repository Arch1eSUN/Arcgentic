---
name: close-round
description: Use only after an arcgentic round has an external audit PASS and state.yaml is in passed. Anchors the verdict, runs strict audit-check, transitions passed to closed, and records the last passed round without writing an external audit verdict.
---

# close-round

Closes an arcgentic round after external audit PASS. This is an orchestrator-owned
closeout seam, not a developer or auditor task.

## Preconditions

1. `.agentic-rounds/state.yaml` has `current_round.state: passed`.
2. `current_round.audit_verdict.outcome` is `PASS`.
3. `current_round.audit_verdict.commit` is set to the audit commit.
4. The verdict file exists and passes both:
   - `arcgentic verdict-completeness <verdict.md>`
   - `arcgentic audit-check <verdict.md> --strict --strict-extended`

## Command

```bash
arcgentic close-round \
  --state-file .agentic-rounds/state.yaml \
  --verdict <docs/audits/round-verdict.md> \
  --audit-commit <audit-commit-sha>
```

## Outputs

- `current_round.state` becomes `closed`.
- `current_round.state_history` gains a `closed` entry.
- `last_passed_round` records round id, audit commit, verdict doc, and close time.
- The command prints a next-round recommendation for the orchestrator.

## Boundaries

- Do not run before external audit PASS.
- Do not write, edit, or replace the external audit verdict.
- Do not use close-round to resolve NEEDS_FIX or AUDIT_INCOMPLETE.
- Do not perform release tagging, publishing, or next-round planning unless the
  user explicitly starts that separate orchestrator step.
