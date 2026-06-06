---
name: codex-thread-orchestration
description: Use when running Arcgentic V2 in Codex and the current thread must orchestrate fixed Planner, Developer, and Auditor role threads.
---

# codex-thread-orchestration

Use this skill only in Codex host mode. The current thread is the
`Orchestrator`.

## Contract

V2 uses exactly four host-visible thread titles:

- `Orchestrator`
- `Planner`
- `Developer`
- `Auditor`

Never create `R1 Developer`, `R2 Auditor`, or other round-numbered thread names.
Round identity lives in `.agentic-rounds/state.yaml` and in the role prompt.

`close-round` is an orchestrator-owned command after anchored PASS. It is not a
thread role.

## Procedure

1. Run:

   ```bash
   arcgentic v2-session-plan --state .agentic-rounds/state.yaml --host codex
   ```

2. For each action in `actions`:

   - `reuse`: send `prompt` to `thread_id`.
   - `create`: create a Codex project thread, set its title to `title`, send
     `prompt`, then record the returned id:

     ```bash
     arcgentic v2-record-session \
       --state .agentic-rounds/state.yaml \
       --host codex \
       --role <role> \
       --thread-id <created-thread-id>
     ```

3. Wait for the role thread to complete and read its latest result.

4. Require the role thread to return a `RoleReturnSignal` JSON object:

   ```json
   {
     "role": "developer",
     "status": "completed",
     "round_id": "R1",
     "state": "awaiting_audit",
     "artifacts": {
       "self_audit": "docs/audits/R1-self-audit.md"
     },
     "next_recommended_role": "auditor"
   }
   ```

5. Record the signal:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-json '<RoleReturnSignal JSON>'
   ```

6. Re-run `v2-session-plan` and dispatch the next role.

## Routing

- `intake` / `planning` / `passed` / `closed` → `Planner`
- `awaiting_dev_start` / `dev_in_progress` / `needs_fix` / `fix_in_progress` → `Developer`
- `awaiting_audit` / `audit_in_progress` → `Auditor`

The auditor decides PASS / NEEDS_FIX / AUDIT_INCOMPLETE. The planner decides
whether the current phase is complete and what the next phase is. The developer
handles implementation, fixes, and self-audit.

## Verification

Before advancing:

1. Read `.agentic-rounds/state.yaml`.
2. Confirm every created thread id is recorded under
   `project.arcgentic_v2.role_sessions`.
3. Confirm every recorded title is one of the four fixed titles.
4. Confirm `last_signal.role` matches the role thread that returned.
5. Confirm `next_role` matches the routing rule.
