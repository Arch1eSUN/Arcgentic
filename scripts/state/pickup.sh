#!/usr/bin/env bash
# scripts/state/pickup.sh — read state.yaml, emit "you should do X" guidance.
#
# Usage:
#   pickup.sh --state-file PATH [--json]
#
# Default: human-readable text. --json: structured output for sub-agents.

set -uo pipefail
ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ARCGENTIC_ROOT/scripts/lib/python.sh"

STATE_FILE=""
JSON_OUT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --state-file) STATE_FILE="$2"; shift 2 ;;
    --json)       JSON_OUT=1; shift ;;
    -h|--help)    grep '^# ' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$STATE_FILE" ] || [ ! -f "$STATE_FILE" ]; then
  echo "Usage: $0 --state-file PATH [--json]" >&2
  exit 2
fi

PYTHON_BIN="$(arcgentic_python)" || exit 1
"$PYTHON_BIN" - "$STATE_FILE" "$JSON_OUT" <<'PY'
import json
import re
import sys

state_file, json_out = sys.argv[1], int(sys.argv[2])

_FIELD_RE = re.compile(r"^(\s*)([A-Za-z0-9_]+):(?:\s*(.*))?$")


def _clean(value):
    value = (value or "").strip()
    if value in {"", "null", "None"}:
        return ""
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value


def _read_state_fields(path):
    fields = {}
    stack = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            match = _FIELD_RE.match(raw_line.rstrip("\n"))
            if not match:
                continue
            indent = len(match.group(1))
            key = match.group(2)
            value = _clean(match.group(3))
            while stack and indent <= stack[-1][0]:
                stack.pop()
            path_tuple = tuple([entry[1] for entry in stack] + [key])
            if value:
                fields[path_tuple] = value
            else:
                stack.append((indent, key))
    return fields

fields = _read_state_fields(state_file)
state = fields.get(("current_round", "state"), "")
project = fields.get(("project", "name"), "<unnamed>")
round_id = fields.get(("current_round", "id"), "")

# State → role + action mapping
guidance = {
    "intake": {
        "role": "founder",
        "action": "State the round scope: name, goal, in-scope/out-of-scope.",
        "next_state": "planning",
        "skill": "arcgentic:orchestrate-round (intake handler)",
    },
    "planning": {
        "role": "planner",
        "action": "Write the round handoff document (16-section pattern) at the project's plans_dir.",
        "next_state": "awaiting_dev_start",
        "skill": "arcgentic:plan-round (future) — for MVP: arcgentic:orchestrate-round dispatches planner-agent",
    },
    "awaiting_dev_start": {
        "role": "orchestrator",
        "action": "Await founder confirmation to start dev session, OR dispatch developer sub-agent immediately.",
        "next_state": "dev_in_progress",
        "skill": "arcgentic:orchestrate-round",
    },
    "dev_in_progress": {
        "role": "developer",
        "action": "Execute the handoff doc task-by-task, write self-audit, and create a local commit anchor.",
        "next_state": "awaiting_test | awaiting_audit",
        "skill": "arcgentic:execute-round (future) — for MVP: dev session reads handoff manually",
    },
    "awaiting_test": {
        "role": "orchestrator",
        "action": "Dispatch Test for realistic simulated user/session testing.",
        "next_state": "test_in_progress",
        "skill": "arcgentic:orchestrate-round",
    },
    "test_in_progress": {
        "role": "test",
        "action": "Run realistic user/session flows, write a user-test report, and return pass/fix routing.",
        "next_state": "awaiting_audit | needs_fix",
        "skill": "arcgentic:test-round (V2 role prompt)",
    },
    "awaiting_audit": {
        "role": "orchestrator",
        "action": "Dispatch lesson-codifier (scan last N rounds), then dispatch auditor.",
        "next_state": "audit_in_progress",
        "skill": "arcgentic:orchestrate-round",
    },
    "audit_in_progress": {
        "role": "auditor",
        "action": "Read handoff + commit chain. Write verdict with fact table. Mechanical-verify every fact.",
        "next_state": "passed | needs_fix",
        "skill": "arcgentic:audit-round",
    },
    "needs_fix": {
        "role": "founder",
        "action": "Acknowledge NEEDS_FIX. Trigger fix round (narrow scope, only auditor findings).",
        "next_state": "fix_in_progress",
        "skill": "(human decision)",
    },
    "fix_in_progress": {
        "role": "developer",
        "action": "Fix ONLY the auditor's findings. No scope creep. Sibling-doc sweep applies.",
        "next_state": "awaiting_test | awaiting_audit",
        "skill": "arcgentic:execute-round (future) with fix-round-narrowness reference",
    },
    "passed": {
        "role": "lesson-codifier",
        "action": "Apply codification protocol: update streak / declare NOVEL type / propose mandate.",
        "next_state": "closed",
        "skill": "arcgentic:codify-lesson (future) — for MVP: auditor handles inline",
    },
    "closed": {
        "role": "(round complete)",
        "action": "Refresh CLAUDE.md / state.yaml prior-round-anchor. Start next round.",
        "next_state": "(none)",
        "skill": "(human decision)",
    },
}

g = guidance.get(state, {"role": "unknown", "action": "(unrecognized state)", "next_state": "?", "skill": "?"})

if json_out:
    print(json.dumps({
        "project": project,
        "round_id": round_id,
        "current_state": state,
        "role": g["role"],
        "action": g["action"],
        "next_state": g["next_state"],
        "skill": g["skill"],
    }, indent=2))
else:
    print(f"=== arcgentic pickup ===")
    print(f"Project:        {project}")
    print(f"Round id:       {round_id or '(unset — intake)'}")
    print(f"Current state:  {state}")
    print(f"")
    print(f"Role to assume: {g['role']}")
    print(f"What to do:     {g['action']}")
    print(f"Next state:     {g['next_state']}")
    print(f"Relevant skill: {g['skill']}")
PY
