# Built-in gate catalog

## 1. `handoff-doc-gate.sh`

**Triggered on**: `planning → awaiting_dev_start`

**State fields read**:
- `project.root`
- `current_round.handoff_doc.path` (relative to project.root)
- `current_round.handoff_doc.sections_present`
- `current_round.handoff_doc.sections_required`

**Pass criteria**:
- handoff file exists at `<project.root>/<handoff_doc.path>`
- `sections_present >= sections_required`

**Failure modes**:
- `current_round.handoff_doc.path is not set` — planner didn't fill in
- `handoff file not found: <path>` — handoff doc not committed yet
- `sections_present N < M required` — handoff incomplete

**Extension**: project-specific gates may add semantic section checks (e.g. "§ 7 must contain ≥ 5 mechanical facts"). Write a separate gate (e.g. `handoff-rich-content-gate.sh`) and chain it via state.yaml.

## 2. `round-commit-chain-gate.sh`

**Triggered on**: `dev_in_progress → awaiting_audit`, `fix_in_progress → awaiting_audit`

**State fields read**:
- `project.root`
- `current_round.expected_dev_commits`
- `current_round.dev_commits` (list of SHA-1)

**Pass criteria**:
- `expected_dev_commits` is set + ≥ 1
- `len(dev_commits) >= expected_dev_commits`
- every SHA in `dev_commits` resolves via `git cat-file -e` in `project.root`

**Failure modes**:
- `expected_dev_commits not set or < 1` — round scope didn't declare commit count
- `dev_commits count N < M expected` — developer didn't commit the full chain
- `commit not found in repo: <SHA>` — fake/typo SHA OR commits in a different repo

**Extension**: project-specific gates can verify commit-message conventions (e.g. "every dev commit must reference the round id"). Write a gate that greps commit messages.

## 3. `verdict-fact-table-gate.sh`

**Triggered on**: `audit_in_progress → passed | needs_fix`

**State fields read**:
- `project.root`
- `current_round.audit_verdict.{path, outcome, fact_table_total, fact_table_pass, findings}`

**Pass criteria**:
- verdict file exists
- `fact_table_pass == fact_table_total`
- if `outcome=="PASS"`: no `findings[].priority` in {P0, P1}
- if `outcome=="NEEDS_FIX"`: always passes (NEEDS_FIX is a legitimate transition)

**Failure modes**:
- `audit_verdict is not set` — auditor hasn't written verdict
- `verdict file not found` — verdict not committed
- `fact_table_pass N < M total` — some facts didn't mechanically verify
- `PASS outcome but blocker findings present` — auditor contradiction (PASS + P0/P1 = impossible)

**Extension**: project-specific gates can verify finding-id conventions (e.g. "every P2 must have a tech-debt registry entry").

## Anatomy of a gate script (template for new gates)

```bash
#!/usr/bin/env bash
# scripts/gates/<gate-name>.sh — <one-line description>.
#
# Triggered on: <state> → <state>
# State fields read: <list>
# Pass criteria: <bullets>

set -uo pipefail

STATE_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --state-file) STATE_FILE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$STATE_FILE" ] && { echo "Usage: $0 --state-file PATH" >&2; exit 2; }

ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"

# ... your checks ...

if <pass condition>; then
  echo "Gate PASS: <reason summary>"
  exit 0
else
  echo "Gate FAIL: <reason>" >&2
  exit 1
fi
```

Every gate has an accompanying `*.test.sh` covering at least 1 PASS case + 2 distinct FAIL cases.
