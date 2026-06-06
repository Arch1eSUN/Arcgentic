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
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --user-request '<current user request>'
   ```

   This must happen before source inspection, test runs, git-log verification,
   or summaries of prior closed rounds.

2. If `orchestrator_status` is `sleeping`, stop immediately. The
   Orchestrator is waiting for `pending_role` to return a `RoleReturnSignal`;
   do not dispatch another role and do not do the pending role's work inline.

3. If `orchestrator_status` is `active`, dispatch the single action in
   `actions`:

   - `reuse`: send `prompt` to `thread_id`.
   - `create`: create a Codex project thread in the current project/workspace,
     set its title to `title`, send `prompt`, then record the returned id:

     ```bash
     arcgentic v2-record-session \
       --state .agentic-rounds/state.yaml \
       --host codex \
       --role <role> \
       --thread-id <created-thread-id>
     ```

   Do not use projectless threads for Arcgentic role sessions. If the created
   thread does not show the current project `cwd`, archive it and recreate it
   under the current project.

   Use the strongest available Codex model for real Planner / Developer /
   Auditor work. Do not default role threads to a lightweight or spark model
   unless the user explicitly asks for a low-cost smoke test. If the host tool
   supports a model override, choose the best available model. If unsure, omit
   the override so the current project/session default is preserved rather than
   downgraded.

4. After sending the role prompt, put the Orchestrator to sleep:

   ```bash
   arcgentic v2-dispatch-role \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --role <role> \
     --thread-id <thread-id>
   ```

   End the Orchestrator turn here. Do not wait in the Orchestrator thread and
   do not dispatch another role. The next Orchestrator turn starts only after
   the role thread returns information.

5. When the role thread returns, read its latest result.

   If the role thread does not return promptly, send one status/constraint
   tightening message that repeats the required role boundary and
   `RoleReturnSignal` shape. If it still does not return a valid signal, stop
   with a role-timeout report. Do not perform that role's work in the
   Orchestrator.

6. Require the role thread to return a `RoleReturnSignal` JSON object:

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

7. Record the signal. This wakes the Orchestrator and clears the pending
   dispatch:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-json '<RoleReturnSignal JSON>'
   ```

   Treat rejection from this command as authoritative. Do not edit the signal
   by hand unless the same role thread explicitly returns a corrected signal.

8. Re-run `v2-session-plan` and dispatch the next role if the plan is active.

## Routing

- `intake` / `planning` / `passed` / `closed` → `Planner`
- `awaiting_dev_start` / `dev_in_progress` / `needs_fix` / `fix_in_progress` → `Developer`
- `awaiting_audit` / `audit_in_progress` → `Auditor`

When a new user request arrives while `current_round.state` is `closed`, route
to Planner. Planner decides whether this is a new phase, a new round, or a
status-only no-op. The Orchestrator must not treat `closed` as permission to
answer from the previous round without Planner.

The auditor decides PASS / NEEDS_FIX / AUDIT_INCOMPLETE. The planner decides
whether the current phase is complete and what the next phase is. The developer
handles implementation, fixes, and self-audit.

Role-specific returns are stricter than generic routing:

- Planner may return only `awaiting_dev_start` with next `Developer`, or
  `planning` with next `Planner`.
- Developer may return only `awaiting_audit` with next `Auditor`, or
  `needs_fix` with next `Developer`.
- Auditor may return only `passed` with next `Planner`, `needs_fix` with next
  `Developer`, or `audit_in_progress` with next `Auditor`.
- A role signal is stale if the current round state no longer belongs to that
  role. Stale signals must be rejected, not merged.
- `RoleReturnSignal` must contain only `role`, `status`, `round_id`, `state`,
  `artifacts`, and `next_recommended_role`.

The Orchestrator may update `.agentic-rounds/state.yaml` and session registry
only. It must not create implementation files, test files, handoff documents,
self-audits, or external audit verdicts.

## Verification

Before advancing:

1. Read `.agentic-rounds/state.yaml`.
2. Confirm every created thread id is recorded under
   `project.arcgentic_v2.role_sessions`.
3. Confirm every recorded title is one of the four fixed titles.
4. Confirm `last_signal.role` matches the role thread that returned.
5. Confirm `next_role` matches the routing rule.
6. Confirm every role thread is project-scoped to the same repo as the
   orchestrator.
