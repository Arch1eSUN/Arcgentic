---
name: session-mode
description: Use when a project has not yet stored session mode, when a user asks for complete arcgentic workflow execution, or when role identity handoff prompts are needed.
---

# session-mode

Resolves project-level single-session vs multi-session execution and prints
role-specific identity prompts. Once `project.session_mode` is present in
`.agentic-rounds/state.yaml`, do not ask again per round.

## Workflow

1. Read `.agentic-rounds/state.yaml` and the round handoff.
2. If `project.session_mode.mode` is already set, treat it as fact and skip the
   recommendation/choice step.
3. If no project-level mode exists, generate a recommendation:

   ```bash
   arcgentic session-mode recommend \
     --round <round-id> \
     --handoff <handoff-path>
   ```

4. Print recommendation, confidence, reasons, suggested role identities, and override
   instructions before asking the user to choose.
5. Print only the identity handoff prompt needed for the next role:

   ```bash
   arcgentic session-mode prompt \
     --round <round-id> \
     --handoff <handoff-path> \
     --mode multi-session \
     --role developer
   ```

   V1 valid roles: `developer`, `auditor`, `closeout`.

6. For V2 Codex-native orchestration, generate the fixed-role host plan instead
   of per-round role prompts:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host codex
   ```

   V2 session roles are fixed to `Orchestrator`, `Planner`, `Developer`, and
   `Auditor`. `close-round` is an orchestrator-owned command, not a session
   role.

## Boundaries

- Do not enter developer work before the mode gate is resolved.
- Do not re-ask the user when project-level mode is already stored.
- Do not claim single-session auto-audit when dispatch transport is unavailable.
- In V1, developer, auditor, and closeout identity prompts must remain separate.
- In V2, keep exactly four fixed role sessions and never create round-numbered
  role threads.
