---
name: execute-round
description: Use when a planned round handoff exists and needs to be implemented end-to-end via the 4-commit chain (entry-admin → BA design → dev body with inline CR + SE → state refresh + self-audit). Dispatches ba-designer / developer / cr-reviewer / se-contract sequentially.
---

# execute-round

Orchestrates the 4-commit chain for an arcgentic round per spec § 4.2.3. Reads the planned
handoff (from `plan-round` skill or hand-authored), then executes Phase 1-4 via the
`arcgentic` Python CLI.

## When to invoke

- User says "let's execute round R{N}" or "run the 4-commit chain for the handoff at ..."
- User runs `/execute-round <round_name>` slash command
- A handoff doc exists at `docs/superpowers/plans/...` and dev work is ready to start

## Prerequisites

Requires the `arcgentic` CLI:
- Stable: `pipx install arcgentic`
- Dev: `cd toolkit && pip install -e ".[dev]"`

Requires a planned handoff doc — run `/plan-round` first if missing.

## Inputs

Parse from `$ARGUMENTS`:
- `round_name` (e.g. "R10-L3-aletheia")
- `handoff_path` (defaults to most recent `docs/superpowers/plans/{date}-{round}-handoff.md`)
- `--dry-run` flag (optional; skip all commits and pushes)

## Workflow

When invoked:

1. Verify the handoff doc exists at `handoff_path`.
2. Shell out:
   ```
   arcgentic execute-round-impl --round=$ROUND --handoff=$HANDOFF_PATH [--dry-run]
   ```
3. The CLI orchestrates 4 phases:
   - **Phase 1 — Entry-admin commit**: commit handoff + state-row updates
   - **Phase 2 — BA design pass**: dispatch ba-designer → write design doc → commit
   - **Phase 3 — Dev body**: dispatch developer → run 4 quality gates (mypy / pytest / ruff / audit-check) → inline CR step → inline SE step (MANDATE #20: NO BA design in SE brief) → commit
   - **Phase 4 — State refresh + self-audit handoff**: compose self-audit handoff doc → write → commit

4. Read CLI output for result summary (per ExecuteRoundResult.summary()):
   - 4 phase results with commit SHAs
   - CR + SE findings counts
   - Quality gate statuses
   - Self-audit handoff path

5. Report to user: 4 commit SHAs + findings counts + handoff path.

## v0.2.0 P0 known limitations (forward-debts)

- **ER-RETRY**: no retry-with-context loops; if any sub-agent dispatch fails, the run aborts. Re-invoke after fixing the failure manually.
- **ER-AUDIT-GATE-4**: quality gate 4 (`arcgentic audit-check`) is SKIPPED — the audit-check engine ships in sub-phase d.1. Reports DONE_WITH_CONCERNS to flag the deviation.
- **ER-AUDIT-FACTS**: self-audit's § 7 mechanical audit facts table is skeletoned with TODO markers. Real auto-generation ships when audit-check integrates.
- **ER-STATE-ROW**: Phase 1's CLAUDE.md state-row update is a NO-OP (project-agnostic).

See `docs/tech-debt.md` for the full forward-debt registry.

## Failure modes

- **Missing handoff doc**: re-run `/plan-round` first.
- **CLI not installed**: instruct user to `pipx install arcgentic`.
- **Sub-agent dispatch failure**: re-invoke after fixing (no automatic retry in v0.2.0 P0).
- **Quality gate FAIL**: developer output had errors; review BA design + fix dev output manually; re-invoke.

## See also

- `agents/ba-designer.md` / `developer.md` / `cr-reviewer.md` / `se-contract.md` — agents dispatched
- `templates/ba_design.md` / `self_audit_handoff.md` — output structure templates
- `toolkit/src/arcgentic/skills_impl/execute_round.py` — Python algorithm
- spec § 4.2 — full skill specification (v0.2.0 P0 is scope-reduced; see ER-* forward-debts)
