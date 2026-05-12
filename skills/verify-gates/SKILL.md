---
name: verify-gates
description: Runs the mechanical quality gates that the arcgentic state machine requires for state transitions. Invoked indirectly by transition.sh OR directly by orchestrator agent before declaring a state transition. Use when about to call transition.sh OR when manually verifying that a round artifact meets the gate criteria. Each gate is a single Bash script; output is PASS/FAIL with reason.
---

# Verify gates

## What this skill does

arcgentic's state machine has 4 gates (MVP):

| Gate | Transition | Verifies |
|------|------------|----------|
| `handoff-doc-gate.sh` | `planning → awaiting_dev_start` | handoff doc exists + has all required sections |
| `round-commit-chain-gate.sh` | `dev_in_progress → awaiting_audit` (also `fix_in_progress → awaiting_audit`) | dev_commits count ≥ expected + every SHA resolves in git |
| `verdict-fact-table-gate.sh` | `audit_in_progress → passed | needs_fix` | verdict file exists + fact_table_pass==total + PASS outcome has no P0/P1 findings |

`transition.sh` runs the required gate automatically. This skill is for the orchestrator (or human) when they want to pre-verify before attempting the transition.

## When to invoke this skill

- About to ask a sub-agent to attempt a state transition → invoke this skill first, run the gate, fix any failures, then transition
- A transition failed and the orchestrator wants to know WHY → invoke this skill, run the relevant gate, read the failure reason
- Setting up a new gate for a project-specific transition → this skill's `references/gate-script-catalog.md` shows the gate-script shape

## Gate script contract

Every gate script:
1. Takes `--state-file PATH` as its only argument
2. Reads state.yaml + does whatever check it does
3. Exits 0 on PASS, 1 on FAIL
4. Prints PASS line to stdout, FAIL reason to stderr

This contract means gates are composable. You can chain them. You can write project-specific ones in your own `<project>/.agentic-rounds/gates/` and reference them in state.yaml's `states.<state>.gate` field.

## Run a gate manually

```bash
bash $PLUGIN_ROOT/scripts/gates/handoff-doc-gate.sh \
  --state-file <project>/.agentic-rounds/state.yaml
echo "exit: $?"
```

## Adding a project-specific gate

1. Write `<project>/.agentic-rounds/gates/your-gate.sh` following the contract above
2. Edit state.yaml: set `states.<source-state>.gate` to `your-gate.sh`
3. Run `transition.sh --gates-dir <project>/.agentic-rounds/gates ...` (override built-in gates dir)

## See also

`references/gate-script-catalog.md` — catalog of built-in gates with anatomy + extension hooks
