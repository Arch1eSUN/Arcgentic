---
name: codex-thread-orchestration
description: Use when running Arcgentic V2 in Codex and the current thread must orchestrate fixed Planner, Developer, Test, and Auditor role threads.
---

# codex-thread-orchestration

Use this skill only in Codex host mode. The current thread is the
`Orchestrator`.

## Contract

V2 uses exactly five host-visible thread titles:

- `Orchestrator`
- `Planner`
- `Developer`
- `Test`
- `Auditor`

Never create `R1 Developer`, `R2 Test`, `R3 Auditor`, or other round-numbered
thread names. Round identity lives in `.agentic-rounds/state.yaml` and in the
role prompt.

Phase/project close is Orchestrator-owned after Planner declares that a phase
or the full project is complete. It is not a per-round role and it must not run
after every Auditor PASS.

## Procedure

1. Rename the current Codex thread to exactly `Orchestrator`, then ensure
   `.agentic-rounds/state.yaml` records the current thread as `Orchestrator`
   before dispatching any role:

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
   If the host cannot rename the current thread, stop because the fixed-role
   thread set is not visible to the user.
   If this thread was created from a Codex delegation payload, the
   `source_thread_id` is not the current Orchestrator id. It is the upstream
   supervising thread id and must not be recorded as the push-return target.
   When correcting only this mistake, use:

   ```bash
   arcgentic v2-record-session \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --role orchestrator \
     --thread-id <current-orchestrator-thread-id> \
     --title Orchestrator \
     --repair-current-orchestrator
   ```

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

4. If `orchestrator_status` is `active` and `actions` is empty, branch by state:
   - `passed`: stop and report that the round PASS cannot advance because the
     state has no usable `project.arcgentic_v2.project_plan`. Do not close the
     round. A valid project plan lets `v2-session-plan` advance to the next
     round or Planner phase-boundary decision.
  - `closed`: stop. The round is terminal and all role threads should be idle.
     Only a new user request may wake Orchestrator and route to Planner.
   - any other state: stop and report the stop state. Do not create a role
     thread manually. This is how Arcgentic prevents loops such as a repeated
     `AUDIT_INCOMPLETE` for the same unresolved evidence gap.

5. If `orchestrator_status` is `active`, dispatch the single action in
   `actions`:

   - `reuse`: send `prompt` to `thread_id`.
   - `create`: create a Codex project thread using the current workspace root
     path as the Codex `projectId`, set its title to `title`, send `prompt`,
     then record the returned id:

     ```bash
     arcgentic v2-record-session \
       --state .agentic-rounds/state.yaml \
       --host codex \
       --role <role> \
       --thread-id <created-thread-id>
     ```

   In Codex, the saved project id is the current workspace root path exposed by
   the thread `cwd`. Do not search thread lists to infer a separate project id.
   Do not use projectless threads for Arcgentic role sessions. If the created
   thread does not show the current project `cwd`, archive it and recreate it
   under the current project.
   Before creating a role thread, re-read `.agentic-rounds/state.yaml` and
   confirm that the same role is still unrecorded and that
   `orchestrator_status` is still `active`. If another turn has already
   recorded that fixed role, reuse the recorded thread. If the Orchestrator is
   now `sleeping`, stop; do not create a recovery duplicate.

   Supervising or recovery sessions must not create Planner / Developer / Test
   / Auditor threads on behalf of an in-progress Orchestrator turn. They may
   send one constraint-tightening message to the Orchestrator, then wait or
   report a timeout. Creating a role thread outside the Orchestrator creates
   duplicate role ownership and invalidates the workflow evidence.

   Use the strongest available Codex model for real Planner / Developer /
   Test / Auditor work. Do not default role threads to a lightweight or spark
   model unless the user explicitly asks for a low-cost smoke test. If the host
   tool supports a model override, choose the best available model. If unsure,
   omit the override so the current project/session default is preserved rather
   than downgraded.

6. After sending the role prompt, put the Orchestrator to sleep:

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

7. When the role thread completes, it must actively send its return message to
   the Orchestrator thread. The Orchestrator must not poll role threads to
   discover completion.

   If the role thread does not return promptly, send one status/constraint
   tightening message that repeats the required role boundary and
   `RoleReturnSignal` shape. If it still does not return a valid signal, stop
   with a role-timeout report. Do not perform that role's work in the
   Orchestrator.

8. Require the role thread to produce natural-language role output plus exactly
   one machine-readable footer:

  Planner example. Planner must produce the complete project phase/round plan
  and a detailed Markdown handoff for the first/current round. Before writing
  the handoff, Planner must:

  - search GitHub or equivalent public sources for reliable comparable projects
    or effective implementation references;
  - scan locally available skills, plugins, MCP servers, connectors, and CLI
    tools that can help this project;
  - choose which references/tools are used this round, which are considered but
    rejected, and why;
  - write those decisions into the handoff so Developer, Test, and Auditor can
    read the artifact instead of relying only on the Orchestrator prompt.

  The Orchestrator transfers prompt instructions between threads, but the role
  prompt must tell the receiving session to read the referenced handoff artifact
  before acting.

   ```text
   R1 plan is ready.

   - Plan artifact: docs/plans/R1.md
   - Scope: build the smallest working CLI and verify it through command-level tests.
   - Next role: Developer should implement from the handoff and return a self-audit.
   ```

   ```arcgentic-role-return
   {
     "role": "planner",
     "status": "planned",
     "round_id": "R1",
     "state": "awaiting_dev_start",
     "artifacts": {
       "handoff": "docs/plans/R1.md",
       "project_plan": {
         "phases": [
           {
             "id": "P1",
             "rounds": [
               {
                 "id": "R1",
                 "handoff": "docs/plans/R1.md",
                 "test_gate": {
                   "required": false,
                   "reason": "No separate reality QA gate is needed for this round."
                 }
               }
             ]
           }
         ]
       }
     },
     "next_recommended_role": "developer"
   }
   ```

Planner output should be a readable plan, not raw JSON. Developer output
should be a readable self-audit summary, not raw JSON. Test output should be a
readable simulated user-test report, not raw JSON. Auditor output should be a
readable verdict, not raw JSON. The footer is the routing envelope.

Planner close/project-completion output must write a closeout artifact, create
a local closeout commit, verify `git rev-parse HEAD`, and include both
`artifacts.closeout` and `artifacts.commit` in the return footer. A closed
project uses `"next_recommended_role": null`; it must not recommend Planner
again unless there is a genuinely new user request.

Developer must not return from a purely working-tree state. After
implementation and verification, Developer must stage the round-owned files,
create a normal local Git commit, verify `git rev-parse HEAD`, write the
self-audit, and include both artifacts in the return footer.

If `project_plan.test_gate.required` for the current round is true, Developer
routes to Test:

```arcgentic-role-return
{
  "role": "developer",
  "status": "completed",
  "round_id": "R1",
  "state": "awaiting_test",
  "artifacts": {
    "self_audit": "docs/audits/R1-self-audit.md",
    "commit": "<40-hex-local-dev-commit>"
  },
  "next_recommended_role": "test"
}
```

If the current round's Test gate is skipped, Developer routes directly to
Auditor:

```arcgentic-role-return
{
  "role": "developer",
  "status": "completed",
  "round_id": "R1",
  "state": "awaiting_audit",
  "artifacts": {
    "self_audit": "docs/audits/R1-self-audit.md",
    "commit": "<40-hex-local-dev-commit>"
  },
  "next_recommended_role": "auditor"
}
```

A GitHub remote is not required for local audit. It is stronger evidence for
release or CI gates, but the minimum audit anchor is a local immutable commit.

Test is not the external auditor and is not a mandatory per-round step. Test
owns realistic simulated user/session testing only when Planner's project plan
requires it after Developer has produced code, self-audit, and a local commit
anchor. Examples:

- CLI: run representative commands and stdin/argument flows like a user.
- Web/mobile app: launch the app or simulator and drive visible UI flows.
- Agent: run an end-to-end user conversation that exercises the promised task.

If the simulated user flow passes, Test writes a report and routes to Auditor:

```arcgentic-role-return
{
  "role": "test",
  "status": "user_tested",
  "round_id": "R1",
  "state": "awaiting_audit",
  "artifacts": {
    "user_test": "docs/tests/R1-user-test.md",
    "commit": "<40-hex-local-dev-commit>"
  },
  "next_recommended_role": "auditor"
}
```

If the simulated user flow fails, Test writes the failed user-test report and
routes to `needs_fix` / `Developer`.

9. Record the signal. This wakes the Orchestrator and clears the pending
   dispatch:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-text '<role return message including arcgentic-role-return block>'
   ```

   Treat rejection from this command as authoritative. Do not hand-extract or
   hand-repair JSON in the Orchestrator unless the same role thread explicitly
   returns a corrected message.

10. After an Auditor PASS return, do not close the round. Re-run
    `v2-session-plan`. If the stored project plan has another round in the
    current phase, `v2-session-plan` advances to that round and returns a
    Developer action. If the phase has no more rounds, it routes to Planner for
    phase-boundary close / next-phase / project-close decision.

11. Dispatch the next role only if the plan is
    active and contains exactly one action. If it is active with no actions,
    stop and report the stop state.

## Routing

- `intake` / `planning` → `Planner`
- `passed` → Orchestrator advances from `project_plan`: next round Developer,
  or Planner at phase boundary
- `closed` → no role action unless a new work request is present
- `awaiting_dev_start` / `dev_in_progress` / `needs_fix` / `fix_in_progress` → `Developer`
- `awaiting_test` / `test_in_progress` → `Test`
- `awaiting_audit` / `audit_in_progress` → `Auditor`

When a new user request arrives while `current_round.state` is `closed`, route
to Planner only if it asks for new work. Status, inspection, review, or "is
this complete?" requests are terminal idle and must not rewrite
`active_user_request` or dispatch Planner. Without a new work request, `closed`
is terminal idle: do not dispatch Planner, Developer, Test, or Auditor.

The auditor decides PASS / NEEDS_FIX / AUDIT_INCOMPLETE. The test role decides
whether the built product survives realistic simulated user/session testing.
The planner decides whether the current phase is complete and what the next
phase is. The developer handles implementation, fixes, local commit anchors,
and self-audit.

Role-specific returns are stricter than generic routing:

- Planner may return only `awaiting_dev_start` with next `Developer`, or
  `planning` with next `Planner`, or `closed` with no next role for final
  project completion.
- Developer may return only `awaiting_test` with next `Test`,
  `awaiting_audit` with next `Auditor`, or `needs_fix` with next `Developer`.
- Test may return only `awaiting_audit` with next `Auditor`, or `needs_fix`
  with next `Developer`.
- Auditor may return only `passed` with next `Planner`, `needs_fix` with next
  `Developer`, or `audit_in_progress` with next `Auditor`.
- `audit_in_progress` with next `Auditor` is only for retryable audit work. If
  the same missing evidence cannot be resolved by another audit pass, the
  Auditor must route to `needs_fix` / `Developer` when Developer can repair it,
  or return a concise `AUDIT_INCOMPLETE` stop report that the Orchestrator does
  not re-dispatch.
- Auditor PASS fact rows must use lifecycle-stable evidence: committed
  artifacts, fixed git hashes, artifact file contents, state history, and
  test/build output. Do not use mutable live routing fields such as
  `current_round.state`, `project.arcgentic_v2.last_signal.role`, or
  `project.arcgentic_v2.last_signal.state` as PASS facts unless the command
  reads an immutable committed snapshot.
- A role signal is stale if the current round state no longer belongs to that
  role. Stale signals must be rejected, not merged. The only exception is an
  Orchestrator-recorded pending role returning the same state it was asked to
  repair, such as an Auditor repairing the already-`passed` verdict artifact
  before Orchestrator advances the workflow.
- The machine footer must contain only `role`, `status`, `round_id`, `state`,
  `artifacts`, and `next_recommended_role`.

The Orchestrator may update `.agentic-rounds/state.yaml` and session registry
only. It must not create implementation files, test files, handoff documents,
self-audits, or external audit verdicts.

Planner, Developer, Test, and Auditor must not update `.agentic-rounds/state.yaml`,
run transition commands, dispatch roles, consume `RoleReturnSignal`, or close
rounds. They write their role-owned artifacts and return JSON; the Orchestrator
is the only state writer for role returns.

Role threads must not stop after acknowledging their role. They must complete
the role-owned work in the same turn, using tools as needed, and only then
return `RoleReturnSignal`. Developer, Test, and Auditor consume prior-role
artifacts from `project.arcgentic_v2.last_signal.artifacts`.

Role threads must actively wake the Orchestrator when complete by sending their
natural-language return message plus `arcgentic-role-return` footer to the
recorded Orchestrator thread id. This is a push-return protocol, not an
Orchestrator polling protocol.

## Verification

Before advancing:

1. Read `.agentic-rounds/state.yaml`.
2. Confirm every created thread id is recorded under
   `project.arcgentic_v2.role_sessions`.
3. Confirm every recorded title is one of the five fixed titles.
4. Confirm `last_signal.role` matches the role thread that returned.
5. Confirm `next_role` matches the routing rule.
6. Confirm every role thread is project-scoped to the same repo as the
   orchestrator.
