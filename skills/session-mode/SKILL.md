---
name: session-mode
description: Use when a round reaches awaiting_dev_start, when a user asks for complete arcgentic workflow execution, or when developer/auditor identity handoff prompts are needed.
---

# session-mode

Recommends single-session or multi-session execution before developer work starts.

## Workflow

1. Read `.agentic-rounds/state.yaml` and the round handoff.
2. Generate a recommendation:

   ```bash
   arcgentic session-mode recommend \
     --round <round-id> \
     --handoff <handoff-path>
   ```

3. Print recommendation, confidence, reasons, suggested role identities, and override
   instructions before asking the user to choose.
4. If the user chooses multi-session, print identity handoff prompts:

   ```bash
   arcgentic session-mode prompt \
     --round <round-id> \
     --handoff <handoff-path> \
     --mode multi-session
   ```

## Boundaries

- Do not enter developer work before the mode gate is resolved.
- Do not claim single-session auto-audit when dispatch transport is unavailable.
- Developer and auditor identity prompts must remain separate.
