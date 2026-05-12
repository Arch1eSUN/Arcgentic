---
name: using-arcgentic
description: Entry skill for the arcgentic plugin — establishes the four-role workflow (planning / dev+self-audit / external-audit / reference-tracking), the round state machine, and when to switch roles or dispatch sub-agents. Use when starting any session in a project that has .agentic-rounds/state.yaml present, OR when the user mentions arcgentic / round-driven development / external audit / four-role workflow.
---

# Using arcgentic

## Overview

arcgentic is an agentic harness for round-driven development. It turns the four-role engineering workflow into a mechanically-enforced state machine where every transition is gated, every artifact is structured, and every lesson is codified.

**Announce at start:** "I'm using the arcgentic:using-arcgentic skill to navigate the round workflow."

## The Iron Rule

```
BEFORE ANY ACTION IN A ROUND-DRIVEN PROJECT:
1. Read .agentic-rounds/state.yaml (single source of truth)
2. Run scripts/state/pickup.sh — get your role + action
3. Load the role-specific skill if applicable
4. Then act
```

## The Four Roles

| Role | When | Skill | State |
|------|------|-------|-------|
| **planner** | Round intake → handoff doc | `arcgentic:plan-round` (post-MVP) | `intake`, `planning` |
| **developer** | Handoff → commit chain | `arcgentic:execute-round` (post-MVP) | `dev_in_progress`, `fix_in_progress` |
| **auditor** | Commits → verdict | `arcgentic:audit-round` | `awaiting_audit`, `audit_in_progress` |
| **ref-tracker** | Daily git fetch + categorize | `arcgentic:track-refs` (post-MVP) | (continuous) |

For MVP scope, only **auditor** has a dedicated role skill. The other roles are exercised manually by reading the handoff doc and following its discipline.

## Two Operating Modes

### Mode A — Single-session (orchestrator drives all)

Main session loads `arcgentic:orchestrate-round`. Acts as orchestrator. Dispatches sub-agents (`orchestrator.md` → `auditor.md` → ...) via Claude Code's `Task` tool when role-switching is needed. State machine advances after each sub-agent's structured output is verified.

**Use when**: independent developer / small project / no team coordination needed.

### Mode B — Multi-session (humans coordinate)

Each role runs in its own Claude session. Each session loads only its role's skill. State.yaml is the inter-session protocol — every session starts by reading it.

**Use when**: team of humans / different humans want different role contexts / role-specific skill loading must not contaminate other role's contexts.

Both modes share the same state.yaml schema and the same gate scripts.

## State Machine

```
intake → planning → awaiting_dev_start → dev_in_progress → awaiting_audit
                                                                 ↓
                                  closed ← passed ←———— audit_in_progress
                                                                 ↓
                                  awaiting_audit ← fix_in_progress ← needs_fix
```

Every transition runs `scripts/state/transition.sh`, which:
1. Verifies the target is in the current state's `next` list (reject if not)
2. Runs the required gate script (reject if not 0)
3. Updates `current_round.state` + appends to `state_history`

Gates (MVP):
- `planning → awaiting_dev_start` requires `handoff-doc-gate.sh`
- `dev_in_progress → awaiting_audit` requires `round-commit-chain-gate.sh`
- `fix_in_progress → awaiting_audit` requires `round-commit-chain-gate.sh`
- `audit_in_progress → passed | needs_fix` requires `verdict-fact-table-gate.sh`

## What to do RIGHT NOW

The literal first thing to do, every session:

```bash
bash $PLUGIN_ROOT/scripts/state/pickup.sh --state-file ./.agentic-rounds/state.yaml
```

(`$PLUGIN_ROOT` is where this plugin is installed; on Claude Code default: `~/.claude/plugins/arcgentic/`)

The pickup output tells you which role + which action. Then load the corresponding skill (if MVP-supported) or follow the handoff doc.

## Bootstrap (new project)

If `.agentic-rounds/state.yaml` doesn't exist:

```bash
bash $PLUGIN_ROOT/scripts/state/init.sh \
  --project-root . \
  --project-name "<your-project-name>" \
  --round-naming "<your-naming-pattern, e.g. phase.round[.fix]>"
```

This creates the state.yaml in `intake` state. You're ready.

## Cost Discipline (load-bearing)

arcgentic never:
- Calls paid APIs from its scripts
- Starts background processes / daemons / cron
- Pulls references automatically (founder/user triggers `refresh-references.sh` manually)

If a sub-agent dispatched via Task tool tries to break any of these, refuse + report.

## When NOT to use arcgentic

- One-off scripts / throwaway prototypes (overhead > value)
- Projects where every change ships without review (no audit role needed)
- Hobby projects without a "PASS gate" notion (the round model assumes that)

## Skill priority (when multiple apply)

1. `arcgentic:using-arcgentic` (this skill) is the orientation skill — always load first in an arcgentic project
2. Then load the role skill matching `pickup.sh` output
3. `arcgentic:pre-round-scan` is invoked by role skills as their first action; you don't need to load it manually
4. `arcgentic:verify-gates` is invoked by the state-machine scripts, not directly by you

## See also

- `skills/orchestrate-round/SKILL.md` — for orchestrator mode
- `skills/audit-round/SKILL.md` — for auditor role
- `docs/examples/state.example.yaml` — schema reference
- `schema/state.schema.json` — JSON Schema
