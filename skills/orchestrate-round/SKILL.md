---
name: orchestrate-round
description: Main-session orchestrator for arcgentic rounds. Use when in single-session mode and the user wants to drive a round end-to-end without role-switching contexts. Dispatches role sub-agents (planner / developer / auditor / lesson-codifier) via Claude Code Task tool, verifies their structured outputs, and advances the state machine. Use also when manually driving the state machine — this skill is the manual+automated driver.
---

# Orchestrate round

## When to use

- Single-session mode (founder + Claude session = whole team)
- Pre-MVP: any time you want a structured walk-through of round states without writing a custom orchestration
- Whenever you need to remember "what's the next state, what's the next gate, who's the next role"

## When NOT to use

- Multi-session mode where each human handles their own role's session (use `using-arcgentic` instead to navigate)
- You're explicitly playing one role (e.g. just auditing) — load that role's skill directly

## Core loop

```
LOAD pre-round-scan skill → run scan
LOAD state.yaml → identify current_state
DETERMINE next action:
  IF current_state in {intake, planning}:
    → role = planner; dispatch planner-agent (post-MVP) OR write handoff manually
  IF current_state == dev_in_progress:
    → role = developer; dispatch developer-agent (post-MVP) OR execute handoff manually
  IF current_state == awaiting_audit / audit_in_progress:
    → role = auditor; LOAD audit-round skill OR dispatch auditor-agent
  IF current_state == passed:
    → role = lesson-codifier; apply protocol (post-MVP: dedicated agent)
  IF current_state == closed:
    → ROUND COMPLETE; refresh state.yaml prior-round-anchor; start next round
EXECUTE action → wait for structured artifact
VERIFY artifact against state.yaml schema
CALL transition.sh with appropriate gate
LOOP
```

## Sub-agent dispatch (Claude Code Task tool)

Pattern for dispatching `auditor` (MVP-supported):

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

For MVP, only auditor + orchestrator agents exist. Planner / developer / lesson-codifier / ref-tracker dispatch is post-MVP.

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
| Founder confirms round complete | `transition.sh --target closed --by orchestrator` |

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
