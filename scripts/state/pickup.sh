#!/usr/bin/env bash
# scripts/state/pickup.sh — read state.yaml, emit "you should do X" guidance.
#
# Usage:
#   pickup.sh --state-file PATH [--json]
#
# Default: human-readable text. --json: structured output for sub-agents.

set -uo pipefail

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

python3 - "$STATE_FILE" "$JSON_OUT" <<'PY'
import sys, yaml, json
state_file, json_out = sys.argv[1], int(sys.argv[2])

with open(state_file) as f:
    data = yaml.safe_load(f) or {}

state = data.get("current_round", {}).get("state", "")
project = data.get("project", {}).get("name", "<unnamed>")
round_id = data.get("current_round", {}).get("id", "")

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
        "action": "Execute the handoff doc task-by-task with inline self-finalization (BA + CR + SE).",
        "next_state": "awaiting_audit",
        "skill": "arcgentic:execute-round (future) — for MVP: dev session reads handoff manually",
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
        "next_state": "awaiting_audit",
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
