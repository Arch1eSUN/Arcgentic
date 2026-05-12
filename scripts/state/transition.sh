#!/usr/bin/env bash
# scripts/state/transition.sh — drive a state-machine transition.
#
# Usage:
#   transition.sh --state-file PATH --target STATE --by ACTOR [--artifact REF]
#                 [--skip-gates] [--gates-dir DIR]
#
# Exit codes:
#   0  transition successful
#   1  transition refused (not allowed by state machine OR gate failed)
#   2  usage error

set -uo pipefail

STATE_FILE=""
TARGET=""
BY=""
ARTIFACT=""
SKIP_GATES=0
GATES_DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --state-file)  STATE_FILE="$2"; shift 2 ;;
    --target)      TARGET="$2"; shift 2 ;;
    --by)          BY="$2"; shift 2 ;;
    --artifact)    ARTIFACT="$2"; shift 2 ;;
    --skip-gates)  SKIP_GATES=1; shift ;;
    --gates-dir)   GATES_DIR="$2"; shift 2 ;;
    -h|--help)     grep '^# ' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$STATE_FILE" ] || [ -z "$TARGET" ] || [ -z "$BY" ]; then
  echo "Usage: $0 --state-file PATH --target STATE --by ACTOR [--artifact REF] [--skip-gates] [--gates-dir DIR]" >&2
  exit 2
fi

if [ ! -f "$STATE_FILE" ]; then
  echo "Error: state file not found: $STATE_FILE" >&2
  exit 1
fi

# Resolve ARCGENTIC_ROOT
ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
[ -z "$GATES_DIR" ] && GATES_DIR="$ARCGENTIC_ROOT/scripts/gates"

source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"
source "$ARCGENTIC_ROOT/scripts/lib/state.sh"

# Check legality
if ! state_is_transition_allowed "$STATE_FILE" "$TARGET"; then
  CUR=$(state_current_value "$STATE_FILE")
  ALLOWED=$(state_allowed_next "$STATE_FILE")
  echo "Error: transition $CUR → $TARGET not allowed (allowed: $ALLOWED)" >&2
  exit 1
fi

# Check gate
GATE=$(state_required_gate "$STATE_FILE" "$TARGET")
if [ -n "$GATE" ]; then
  if [ "$SKIP_GATES" -eq 1 ]; then
    echo "Warning: skipping gate $GATE (--skip-gates)" >&2
  else
    GATE_PATH="$GATES_DIR/$GATE"
    if [ ! -x "$GATE_PATH" ]; then
      echo "Error: gate script not found or not executable: $GATE_PATH" >&2
      exit 1
    fi
    if ! bash "$GATE_PATH" --state-file "$STATE_FILE"; then
      echo "Error: gate $GATE failed; transition refused" >&2
      exit 1
    fi
  fi
fi

# Apply transition
yaml_set "$STATE_FILE" "current_round.state" "$TARGET"
state_append_history "$STATE_FILE" "$TARGET" "$BY" "$ARTIFACT"

echo "Transitioned to: $TARGET"
exit 0
