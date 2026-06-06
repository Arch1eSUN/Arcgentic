---
name: arcgentic
description: Use when the user says Arcgentic, asks to use Arcgentic, or wants an idea taken through a complete plan → development → self-audit → external audit workflow in Codex.
---

# Arcgentic

This is the Codex-facing entry skill for Arcgentic V2.

Use this before `build-feature`, `executing-plans`, or direct coding whenever
the user asks to use Arcgentic.

Do not directly implement, test, or scaffold the requested feature from the
Orchestrator, even in a greenfield or empty project. Arcgentic work starts by
dispatching Planner.

## Immediate behavior in Codex

1. Treat the current thread as `Orchestrator` and rename the current Codex
   thread to exactly `Orchestrator` before dispatching any role.
2. Determine whether the current thread has a real project/workspace root.
   - If yes, continue with project-scoped orchestration.
   - If no, stop and ask the user to open or create a saved project workspace.
3. If this is the first Arcgentic V2 run in the project and no mode is already
   stored, judge the user's idea before dispatching Planner:
   - Run:

     ```bash
     arcgentic session-mode recommend-v2 --idea '<current user request>'
     ```

   - Present the recommended mode, confidence, reasons, and tradeoff in natural
     language.
   - Ask the user to confirm the recommendation or override it.
   - Do not dispatch Planner until the user has chosen one project-level mode.
4. The two V2 modes are:
   - `single-session-subagent`: faster and usually finishes sooner. Planner,
     Developer, Test, and Auditor run as named subagents inside the current
     Orchestrator session, so audit isolation is weaker. The first use of a
     role creates that fixed named role identity; later rounds reuse it.
   - `multi-session-subthread`: slower. Planner, Developer, Test, and Auditor
     run in fixed project threads, so role separation and external-audit
     evidence are stronger.
5. Use the chosen mode for the whole project. Do not ask again per round unless
   the user explicitly starts a new project or requests a reset.
6. In `multi-session-subthread`, use the current project/workspace as the only
   valid target for role threads after initialization.
7. Do not create projectless Planner / Developer / Test / Auditor threads.
8. Use the strongest available Codex model for real Planner / Developer /
   Test / Auditor work. Do not default role threads to a lightweight or spark
   model unless the user explicitly asks for a low-cost smoke test.
9. Record the current thread as fixed role `Orchestrator` in
   `.agentic-rounds/state.yaml` before dispatching Planner. If the host cannot
   provide the current Orchestrator thread id, stop because push-return cannot
   work.
   In Codex delegation-created threads, do not treat the delegation
   `source_thread_id` as the current Orchestrator id. It identifies the upstream
   supervising thread, not the project-scoped Orchestrator.
10. Before reading implementation files, running tests, checking git log, or
   summarizing prior work, initialize/check `.agentic-rounds/state.yaml` and run
   `v2-session-plan`.
11. Initialize `.agentic-rounds/state.yaml` if it does not exist.
   If state exists and `current_round.state` is `closed`, treat the new user
   request as input for Planner only when it asks for new work. Status,
   inspection, review, or "is this complete?" requests are terminal idle and
   must not rewrite `active_user_request` or dispatch Planner.
12. Run `v2-session-plan` with the user-selected mode on first use, or without
    `--mode` after the mode is already stored:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host codex \
     --user-request '<current user request>' \
     --mode <single-session-subagent|multi-session-subthread>
   ```

13. If the plan is active and contains an action, dispatch that one role before
   any verification or implementation inspection, then call
   `arcgentic v2-dispatch-role` and end the Orchestrator turn in
   `multi-session-subthread`, or create/reuse the named role agent directly in
   `single-session-subagent`.
   If state is `closed` and the plan has no actions, stop: the round is
   terminal at the project level, all role threads are idle, and Orchestrator
   should wait for a new user request.
14. Load `codex-thread-orchestration` and follow it.

## Bootstrap if state is missing

Find the plugin root:

```bash
PLUGIN_ROOT="${ARCGENTIC_PLUGIN_ROOT:-$HOME/plugins/arcgentic}"
```

Then initialize state:

```bash
bash "$PLUGIN_ROOT/scripts/state/init.sh" \
  --project-root . \
  --project-name "$(basename "$PWD")" \
  --round-naming "R<n>"
```

After init, update the state for V2 Codex mode:

```bash
python - <<'PY'
from pathlib import Path
import yaml

path = Path(".agentic-rounds/state.yaml")
state = yaml.safe_load(path.read_text(encoding="utf-8"))
state.setdefault("project", {})["arcgentic_v2"] = {
    "host": "codex",
    "role_sessions": {},
}
path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
PY
```

## Fail-closed rules

- If `arcgentic` CLI is not available, report installation failure instead of
  pretending Arcgentic is active.
- If the current thread is projectless or cannot create project-scoped role
  threads, stop.
- If `.agentic-rounds/state.yaml` records delegation `source_thread_id` as the
  Orchestrator session by mistake, do not create Planner. Repair only that
  field with:

  ```bash
  arcgentic v2-record-session \
    --state .agentic-rounds/state.yaml \
    --host codex \
    --role orchestrator \
    --thread-id <current-orchestrator-thread-id> \
    --title Orchestrator \
    --repair-current-orchestrator
  ```

- If `.agentic-rounds/state.yaml` cannot be created or validated, stop.
- If role threads cannot be created in the current project/workspace, stop.
- If a role thread is slow, send at most one status/constraint-tightening
  message. If it still does not return a valid `RoleReturnSignal`, stop with a
  role-timeout status. Do not continue the workflow in the Orchestrator.
- After dispatching a role prompt, call `arcgentic v2-dispatch-role` and end
  the Orchestrator turn. The Orchestrator resumes only when the pending role
  actively sends return information back to the Orchestrator thread.
- If `arcgentic v2-return-signal` rejects the role output, stop and report the
  rejected signal. Do not repair it by hand in the Orchestrator.
- Do not silently fall back to "Arcgentic-style" hand-written evidence.
- Do not treat "greenfield" or "empty repo" as permission for Orchestrator
  implementation.
- Do not verify, summarize, or inspect a previous closed round as the response
  to a new implementation request. Route the request to Planner first.
- Do not auto-dispatch Planner from project-level `closed` unless there is a
  new user request. Closed without a new request means the project workflow is
  stopped. Round-level PASS is not closed; it must advance through the stored
  project plan.
- Do not run ordinary coding work before Planner has produced or approved the
  round plan.
- Planner, Developer, Test, and Auditor must not mutate `.agentic-rounds/state.yaml`,
  run transition commands, dispatch roles, consume `RoleReturnSignal`, or close
  rounds. They write their role-owned artifacts and return natural-language
  output plus one `arcgentic-role-return` footer for the Orchestrator to consume.
- Role threads must not stop after acknowledging their role. They must complete
  role-owned work in the same turn, using tools as needed, before returning
  `RoleReturnSignal`. Developer, Test, and Auditor consume prior-role artifacts
  from `project.arcgentic_v2.last_signal.artifacts`.
- Role threads must actively wake the Orchestrator by sending their completed
  natural-language output and machine footer to the recorded Orchestrator
  thread. The Orchestrator must not poll role threads to discover completion.
- Planner must do discovery before handoff: search GitHub or equivalent public
  references for reliable comparable projects, scan local skills/plugins/MCP
  servers/connectors/tools, then write the selected references and tools into a
  detailed Markdown handoff. Each downstream role must read the handoff artifact
  named in the Orchestrator prompt before acting.
- Planner project-close returns must write a closeout artifact, create a local
  closeout commit, include `artifacts.closeout` and `artifacts.commit`, and use
  `next_recommended_role: null`. Closed projects are terminal idle unless the
  user provides a genuinely new work request.
- Auditor PASS fact rows must use lifecycle-stable evidence: committed
  artifacts, fixed git hashes, artifact file contents, state history, and
  test/build output. Do not use mutable live routing fields such as
  `current_round.state`, `project.arcgentic_v2.last_signal.role`, or
  `project.arcgentic_v2.last_signal.state` as PASS facts unless the command
  reads an immutable committed snapshot.
- Do not create source files, tests, handoff docs, self-audits, user-test
  reports, or external audit verdicts from the Orchestrator. Those belong to
  Planner, Developer, Test, and Auditor role threads.

## Continue

Load and follow:

- `codex-thread-orchestration` for Codex V2 fixed-role threads.
- `using-arcgentic` for the general round-state vocabulary and state-machine
  rules.
