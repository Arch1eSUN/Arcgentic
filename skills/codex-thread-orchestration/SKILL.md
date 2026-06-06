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

1. Ensure `.agentic-rounds/state.yaml` records the current thread as
   `Orchestrator` before dispatching any role:

   ```bash
   arcgentic v2-record-session \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --role orchestrator \
     --thread-id <current-orchestrator-thread-id> \
     --title Orchestrator
   ```

   If the host cannot provide the current Orchestrator thread id, stop. Without
   this id, Planner / Developer / Auditor cannot actively send completion back.

2. Run:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --user-request '<current user request>'
   ```

   This must happen before source inspection, test runs, git-log verification,
   or summaries of prior closed rounds.

3. If `orchestrator_status` is `sleeping`, stop immediately. The
   Orchestrator is waiting for `pending_role` to return a `RoleReturnSignal`;
   do not dispatch another role and do not do the pending role's work inline.

4. If `orchestrator_status` is `active`, dispatch the single action in
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

5. After sending the role prompt, put the Orchestrator to sleep:

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

6. When the role thread completes, it must actively send its return message to
   the Orchestrator thread. The Orchestrator must not poll role threads to
   discover completion.

   If the role thread does not return promptly, send one status/constraint
   tightening message that repeats the required role boundary and
   `RoleReturnSignal` shape. If it still does not return a valid signal, stop
   with a role-timeout report. Do not perform that role's work in the
   Orchestrator.

7. Require the role thread to produce natural-language role output plus exactly
   one machine-readable footer:

   ```arcgentic-role-return
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

   Planner output should be a readable plan, not raw JSON. Developer output
   should be a readable self-audit summary, not raw JSON. Auditor output should
   be a readable verdict, not raw JSON. The footer is the routing envelope.

8. Record the signal. This wakes the Orchestrator and clears the pending
   dispatch:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-text '<role return message including arcgentic-role-return block>'
   ```

   Treat rejection from this command as authoritative. Do not hand-extract or
   hand-repair JSON in the Orchestrator unless the same role thread explicitly
   returns a corrected message.

9. Re-run `v2-session-plan` and dispatch the next role if the plan is active.

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
- The machine footer must contain only `role`, `status`, `round_id`, `state`,
  `artifacts`, and `next_recommended_role`.

The Orchestrator may update `.agentic-rounds/state.yaml` and session registry
only. It must not create implementation files, test files, handoff documents,
self-audits, or external audit verdicts.

Planner, Developer, and Auditor must not update `.agentic-rounds/state.yaml`,
run transition commands, dispatch roles, consume `RoleReturnSignal`, or close
rounds. They write their role-owned artifacts and return JSON; the Orchestrator
is the only state writer for role returns.

Role threads must not stop after acknowledging their role. They must complete
the role-owned work in the same turn, using tools as needed, and only then
return `RoleReturnSignal`. Developer and Auditor consume prior-role artifacts
from `project.arcgentic_v2.last_signal.artifacts`.

Role threads must actively wake the Orchestrator when complete by sending their
natural-language return message plus `arcgentic-role-return` footer to the
recorded Orchestrator thread id. This is a push-return protocol, not an
Orchestrator polling protocol.

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
