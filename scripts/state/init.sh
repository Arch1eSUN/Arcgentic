#!/usr/bin/env bash
# scripts/state/init.sh — initialize a project's .agentic-rounds/state.yaml.
#
# Usage:
#   init.sh --project-root PATH --project-name NAME --round-naming PATTERN [--force]
#
# Creates <project-root>/.agentic-rounds/state.yaml from the template, with
# project.name + project.round_naming populated. Refuses to overwrite unless
# --force is given.

set -uo pipefail
ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ARCGENTIC_ROOT/scripts/lib/python.sh"

PROJECT_ROOT=""
PROJECT_NAME=""
ROUND_NAMING=""
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --round-naming) ROUND_NAMING="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help)
      grep '^# ' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$PROJECT_ROOT" ]; then
  echo "Error: --project-root is required" >&2
  exit 2
fi
if [ -z "$PROJECT_NAME" ]; then
  echo "Error: --project-name is required" >&2
  exit 2
fi
if [ -z "$ROUND_NAMING" ]; then
  echo "Error: --round-naming is required" >&2
  exit 2
fi

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "Error: project-root does not exist: $PROJECT_ROOT" >&2
  exit 2
fi

STATE_DIR="$PROJECT_ROOT/.agentic-rounds"
STATE_FILE="$STATE_DIR/state.yaml"

if [ -f "$STATE_FILE" ] && [ "$FORCE" -ne 1 ]; then
  echo "Error: $STATE_FILE already exists. Use --force to overwrite." >&2
  exit 1
fi

mkdir -p "$STATE_DIR"

# Resolve absolute path for project.root
PROJECT_ROOT_ABS="$(cd "$PROJECT_ROOT" && pwd)"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

PYTHON_BIN="$(arcgentic_python yaml)" || exit 1
"$PYTHON_BIN" -c '
from pathlib import Path
import sys
import yaml

state_file, project_name, project_root, round_naming, timestamp = sys.argv[1:]
state = {
    "schema_version": "0.1",
    "project": {
        "name": project_name,
        "root": project_root,
        "round_naming": round_naming,
        "paths": {
            "plans_dir": "docs/plans",
            "audits_dir": "docs/audits",
        },
        "verification_command": "",
        "audit_check_command": "",
        "session_mode": None,
    },
    "current_round": {
        "id": "",
        "state": "intake",
        "state_history": [
            {
                "state": "intake",
                "ts": timestamp,
                "by": "init.sh",
            }
        ],
    },
    "states": {
        "intake": {"next": ["planning"]},
        "planning": {"next": ["awaiting_dev_start"], "gate": "handoff-doc-gate.sh"},
        "awaiting_dev_start": {"next": ["dev_in_progress"]},
        "dev_in_progress": {"next": ["awaiting_test", "awaiting_audit"], "gate": "round-commit-chain-gate.sh"},
        "awaiting_test": {"next": ["test_in_progress"]},
        "test_in_progress": {"next": ["awaiting_audit"]},
        "awaiting_audit": {"next": ["audit_in_progress"]},
        "audit_in_progress": {
            "next": ["passed", "needs_fix"],
            "gate": "verdict-fact-table-gate.sh",
        },
        "needs_fix": {"next": ["fix_in_progress"]},
        "fix_in_progress": {"next": ["awaiting_test", "awaiting_audit"], "gate": "round-commit-chain-gate.sh"},
        "passed": {"next": ["closed"]},
        "closed": {"next": []},
    },
    "last_passed_round": None,
    "mandates": [],
    "lessons": [],
    "active_debts": {
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "p3": 0,
    },
}
Path(state_file).write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
' "$STATE_FILE" "$PROJECT_NAME" "$PROJECT_ROOT_ABS" "$ROUND_NAMING" "$TIMESTAMP"

echo "Initialized $STATE_FILE"
exit 0
