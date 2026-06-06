---
name: arcgentic
description: Use when the user says Arcgentic, asks to use Arcgentic, or wants an idea taken through a complete plan → development → self-audit → external audit workflow in Codex.
---

# Arcgentic

This is the Codex-facing entry skill for Arcgentic V2.

Use this before `build-feature`, `executing-plans`, or direct coding whenever
the user asks to use Arcgentic.

## Immediate behavior in Codex

1. Treat the current thread as `Orchestrator`.
2. Use the current project/workspace as the only valid target for role threads.
3. Do not create projectless Planner / Developer / Auditor threads.
4. Use the strongest available Codex model for real Planner / Developer /
   Auditor work. Do not default role threads to a lightweight or spark model
   unless the user explicitly asks for a low-cost smoke test.
5. Initialize `.agentic-rounds/state.yaml` if it does not exist.
6. Run:

   ```bash
   arcgentic v2-session-plan --state .agentic-rounds/state.yaml --host codex
   ```

7. Load `codex-thread-orchestration` and follow it.

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
    "mode": "multi-session-subthread",
    "role_sessions": {},
}
path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
PY
```

## Fail-closed rules

- If `arcgentic` CLI is not available, report installation failure instead of
  pretending Arcgentic is active.
- If `.agentic-rounds/state.yaml` cannot be created or validated, stop.
- If role threads cannot be created in the current project/workspace, stop.
- If a role thread is slow, send at most one status/constraint-tightening
  message. If it still does not return a valid `RoleReturnSignal`, stop with a
  role-timeout status. Do not continue the workflow in the Orchestrator.
- After dispatching a role prompt, call `arcgentic v2-dispatch-role` and end
  the Orchestrator turn. The Orchestrator resumes only when the pending role
  returns information.
- If `arcgentic v2-return-signal` rejects the role output, stop and report the
  rejected signal. Do not repair it by hand in the Orchestrator.
- Do not silently fall back to "Arcgentic-style" hand-written evidence.
- Do not run ordinary coding work before Planner has produced or approved the
  round plan.
- Do not create source files, tests, handoff docs, self-audits, or external
  audit verdicts from the Orchestrator. Those belong to Planner, Developer, and
  Auditor role threads.

## Continue

Load and follow:

- `codex-thread-orchestration` for Codex V2 fixed-role threads.
- `using-arcgentic` for the general round-state vocabulary and state-machine
  rules.
