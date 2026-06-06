---
name: orchestrate-round
description: Main-session orchestrator for arcgentic rounds. Use when in single-session mode, when a project-level session mode must drive dispatch order, or when manually advancing the state machine. Dispatches role sub-agents, verifies structured outputs, and owns PASS-only close-round execution.
---

# Orchestrate round

## When to use

- Single-session mode (founder + Claude session = whole team)
- Multi-session mode when you need the dispatch order and role handoff prompts
- Any time you want a structured walk-through of round states without writing a custom orchestration
- Whenever you need to remember "what's the next state, what's the next gate, who's the next role"

## When NOT to use

- You're explicitly playing one role (e.g. just auditing) — load that role's skill directly

## Core loop

```
LOAD pre-round-scan skill → run scan
LOAD state.yaml → identify current_state
IF project.session_mode is present:
  → use it; do not ask the user for mode again
ELSE:
  → run `arcgentic session-mode recommend`
  → store the project-level decision before dev starts
RUN `arcgentic orchestrator-dispatch --round <round-id> --handoff <path> --mode <mode>`
DETERMINE next action:
  IF current_state in {intake, planning}:
    → role = planner; dispatch planner-agent OR print planner role prompt
  IF current_state in {awaiting_dev_start, dev_in_progress, needs_fix, fix_in_progress}:
    → role = developer; dispatch developer-agent OR print developer role prompt
  IF current_state == awaiting_audit / audit_in_progress:
    → role = auditor; LOAD audit-round skill OR dispatch auditor-agent
  IF current_state == passed:
    → role = planner for next-phase decision OR run orchestrator-owned close-round
  IF current_state == closed:
    → ROUND COMPLETE; refresh state.yaml prior-round-anchor; start next round
EXECUTE action → wait for structured artifact
VERIFY artifact against state.yaml schema
CALL transition.sh with appropriate gate
LOOP
```

## Sub-agent dispatch (Claude Code Task tool)

Pattern for dispatching `auditor`:

```
Use the Task tool with:
  description: "Audit round <round-id>"
  subagent_type: "general-purpose"  # or platform-specific
  prompt: |
    You are the auditor for arcgentic round <round-id>. Your job:
    1. Read $PLUGIN_ROOT/skills/audit-round/SKILL.md and its references/
    2. Read .agentic-rounds/state.yaml
    3. Read the handoff doc at <handoff-path>
    4. Read every commit in <dev_commits>
    5. Produce a verdict file at <verdict-path> following verdict-template.md
    6. Mechanically verify every fact in your fact table
    7. Apply lesson-codification-protocol.md
    8. Update state.yaml's current_round.audit_verdict block
    9. Return: "DONE — verdict at <verdict-path>, outcome <PASS|NEEDS_FIX>"
```

Planner, developer, auditor, lesson-codifier, and ref-tracker agents exist in
the plugin. Dispatch availability still depends on the host environment's Task
tool; when unavailable, print the role prompt and stop for the matching session.

For V1 hardening, use the CLI dispatch plan as the source of role order:

```bash
arcgentic orchestrator-dispatch \
  --round <round-id> \
  --handoff <handoff-path> \
  --mode <single-session|multi-session>
```

In multi-session mode, the order is developer → auditor → closeout. Do not give
the closeout prompt to the developer or auditor session.

## V2 fixed-role Codex session plan

For V2 Codex-native orchestration, do not create per-round session names such
as `R1 Developer` or `R2 Auditor`. The host-visible thread titles stay fixed:

- `Orchestrator`
- `Planner`
- `Developer`
- `Auditor`

Round identity lives in `.agentic-rounds/state.yaml` and in the prompt payload,
not in the thread title. The orchestrator emits the host plan with:

```bash
arcgentic v2-session-plan --state .agentic-rounds/state.yaml --host codex
```

V2 routing rules:

- `needs_fix` / `fix_in_progress` → `Developer`
- `awaiting_audit` / `audit_in_progress` → `Auditor`
- `passed` → `Planner` for phase decision, not a closeout session
- `close-round` remains an orchestrator-owned mechanical command after PASS is
  anchored; it is not a fifth role session

## Verifying sub-agent output

NEVER trust the sub-agent's success report alone. After it returns:

1. `git status` — what files changed?
2. `git diff` — what's the actual content?
3. Read the artifact (verdict / handoff / etc.) directly
4. Run any mechanical fact-table commands the artifact claims passed
5. Run state.yaml schema validation
6. Only THEN advance the state machine

This is the "trust but verify" pattern from superpowers:verification-before-completion, applied to sub-agent outputs.

## State transitions (when to call transition.sh)

| After event | Call |
|---|---|
| Handoff doc committed | `transition.sh --target awaiting_dev_start --by orchestrator --artifact <handoff-path>@<sha>` |
| Dev commits chain committed | `transition.sh --target awaiting_audit --by orchestrator` |
| Auditor verdict committed | `transition.sh --target passed --by orchestrator` (or `--target needs_fix`) |
| External audit PASS is anchored | `arcgentic close-round --state-file .agentic-rounds/state.yaml --verdict <verdict-path> --audit-commit <sha>` |

If `transition.sh` exits non-zero, READ THE ERROR. The state machine refusal is informational. Common reasons:
- Gate failed — fix the gated artifact, re-run transition
- State.yaml inconsistent — schema validation will reveal which field is wrong

## Cost-discipline (in orchestrator role)

When dispatching sub-agents, NEVER include in the prompt:
- Paid-API keys / endpoints
- Instructions to call paid services
- Background-process / daemon spawning

Sub-agents inherit the founder's Claude Code subscription. That's enough.

## References (load on demand)

- `references/state-machine-overview.md` — visual + tabular state machine
- `references/sub-agent-dispatch.md` — full dispatch patterns + prompt templates
- `references/single-vs-multi-session.md` — when to choose which mode

## See also

- `arcgentic:audit-round` — auditor role skill
- `arcgentic:verify-gates` — gate runner skill
- `arcgentic:pre-round-scan` — mandatory prelude
