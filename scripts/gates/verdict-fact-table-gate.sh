#!/usr/bin/env bash
# scripts/gates/verdict-fact-table-gate.sh — audit → passed|needs_fix gate.
#
# Passes iff:
#   current_round.audit_verdict is set
#   .path resolves to existing file
#   .fact_table_pass == .fact_table_total
#   if .outcome=PASS: no P0/P1 findings
#   if .outcome=NEEDS_FIX: always passes the gate (transition to needs_fix is legitimate)

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

PROJECT_ROOT=$(yaml_get "$STATE_FILE" "project.root")
VERDICT_JSON=$(yaml_get "$STATE_FILE" "current_round.audit_verdict")

if [ -z "$VERDICT_JSON" ] || [ "$VERDICT_JSON" = "null" ]; then
  echo "Gate FAIL: current_round.audit_verdict is not set" >&2
  exit 1
fi

python3 - "$VERDICT_JSON" "$PROJECT_ROOT" <<'PY'
import sys, json
verdict = json.loads(sys.argv[1])
project_root = sys.argv[2]

path = verdict.get("path", "")
import os
full = os.path.join(project_root, path)
if not os.path.isfile(full):
    print(f"Gate FAIL: verdict file not found: {full}", file=sys.stderr)
    sys.exit(1)

total = int(verdict.get("fact_table_total", 0))
passed = int(verdict.get("fact_table_pass", 0))
if passed < total:
    print(f"Gate FAIL: fact_table_pass {passed} < {total} total", file=sys.stderr)
    sys.exit(1)

outcome = verdict.get("outcome", "")
findings = verdict.get("findings", []) or []

if outcome == "PASS":
    blockers = [f for f in findings if f.get("priority") in ("P0", "P1")]
    if blockers:
        ids = ", ".join(f"{f['id']}({f['priority']})" for f in blockers)
        print(f"Gate FAIL: PASS outcome but blocker findings present: {ids}", file=sys.stderr)
        sys.exit(1)

print(f"Gate PASS: verdict {outcome}, {passed}/{total} facts, "
      f"{len(findings)} findings ({sum(1 for f in findings if f.get('priority') in ('P2','P3'))} non-blocking)")
sys.exit(0)
PY
