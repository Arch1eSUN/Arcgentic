# State machine overview

## Visual

```
                                ┌─────────┐
                                │ intake  │
                                └────┬────┘
                                     │ founder states scope
                                     ▼
                                ┌────────────┐
                                │  planning  │
                                └──────┬─────┘
                                       │ planner writes handoff
                                       │ [GATE: handoff-doc-gate.sh]
                                       ▼
                            ┌────────────────────┐
                            │ awaiting_dev_start │
                            └──────────┬─────────┘
                                       │ founder triggers dev session
                                       ▼
                            ┌────────────────────┐
                            │  dev_in_progress   │ ←──┐
                            └──────────┬─────────┘    │
                                       │ [GATE: round-commit-chain-gate.sh]
                                       ▼              │
                            ┌────────────────────┐    │
                            │  awaiting_audit    │    │
                            └──────────┬─────────┘    │
                                       │ orchestrator dispatches auditor
                                       ▼              │
                            ┌────────────────────┐    │
                            │ audit_in_progress  │    │
                            └──────────┬─────────┘    │
                                       │ [GATE: verdict-fact-table-gate.sh]
                              ┌────────┴────────┐     │
                              ▼                 ▼     │
                        ┌──────────┐       ┌──────────┐
                        │  passed  │       │ needs_fix│
                        └─────┬────┘       └─────┬────┘
                              │                  │ founder triggers fix
                              ▼                  ▼
                        ┌──────────┐       ┌────────────────────┐
                        │  closed  │       │  fix_in_progress   │
                        └──────────┘       └──────────┬─────────┘
                                                      │ [GATE: round-commit-chain-gate.sh]
                                                      └──────────────┐ (back to awaiting_audit)
                                                                     │
                                                                     ▲
```

## State table

| State | Trigger to enter | Trigger to leave | Required gate on exit | Role responsible |
|-------|------------------|------------------|----------------------|------------------|
| `intake` | round init | founder states scope | — | founder |
| `planning` | scope stated | handoff written | `handoff-doc-gate.sh` | planner |
| `awaiting_dev_start` | handoff PASS | founder triggers dev | — | orchestrator |
| `dev_in_progress` | dev starts | dev commits chain ready | `round-commit-chain-gate.sh` | developer |
| `awaiting_audit` | dev chain ready | auditor dispatched | — | orchestrator |
| `audit_in_progress` | auditor reads inputs | verdict written | `verdict-fact-table-gate.sh` | auditor |
| `passed` | verdict outcome=PASS | founder closes | — | orchestrator + lesson-codifier |
| `needs_fix` | verdict outcome=NEEDS_FIX | fix round starts | — | founder |
| `fix_in_progress` | fix round | fix chain ready | `round-commit-chain-gate.sh` | developer |
| `closed` | round complete | — | — | (round done) |

## Loop on fix rounds

`audit_in_progress → needs_fix → fix_in_progress → awaiting_audit → audit_in_progress` is the fix loop. Most rounds go through 0 or 1 fix iterations; a stubborn round may go through 3+ (R1.5c chain hit 6).

Per `fix-example-vs-contract.md`: the fix round must address the contract's full input domain, not just the auditor's reproducer. Loops > 2 typically indicate failure to apply this pattern.

## State.yaml schema vs state machine

`schema/state.schema.json` defines the data structure of state.yaml. The state machine (above) defines the allowed transitions. They're related but distinct:
- Schema says "state must be one of {intake, planning, ...}" — values
- State machine says "from planning, the only allowed next states are {awaiting_dev_start}" — transitions

Both are enforced: schema by `validate-schema.sh`, transitions by `transition.sh`.
