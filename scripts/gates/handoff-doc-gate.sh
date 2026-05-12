#!/usr/bin/env bash
# scripts/gates/handoff-doc-gate.sh — planning → awaiting_dev_start gate.
#
# Passes iff state.yaml has:
#   current_round.handoff_doc.path → existing file (relative to project.root)
#   current_round.handoff_doc.sections_present >= sections_required
#
# Usage: handoff-doc-gate.sh --state-file PATH

set -uo pipefail

STATE_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --state-file) STATE_FILE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$STATE_FILE" ] && { echo "Usage: $0 --state-file PATH" >&2; exit 2; }
[ ! -f "$STATE_FILE" ] && { echo "Error: state file not found: $STATE_FILE" >&2; exit 1; }

ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"

PROJECT_ROOT=$(yaml_get "$STATE_FILE" "project.root")
HANDOFF_PATH=$(yaml_get "$STATE_FILE" "current_round.handoff_doc.path")
PRESENT=$(yaml_get "$STATE_FILE" "current_round.handoff_doc.sections_present")
REQUIRED=$(yaml_get "$STATE_FILE" "current_round.handoff_doc.sections_required")

if [ -z "$HANDOFF_PATH" ]; then
  echo "Gate FAIL: current_round.handoff_doc.path is not set" >&2
  exit 1
fi

FULL_PATH="$PROJECT_ROOT/$HANDOFF_PATH"
if [ ! -f "$FULL_PATH" ]; then
  echo "Gate FAIL: handoff file not found: $FULL_PATH" >&2
  exit 1
fi

if [ -z "$PRESENT" ] || [ -z "$REQUIRED" ]; then
  echo "Gate FAIL: sections_present or sections_required missing" >&2
  exit 1
fi

if [ "$PRESENT" -lt "$REQUIRED" ]; then
  echo "Gate FAIL: sections_present $PRESENT < $REQUIRED required" >&2
  exit 1
fi

echo "Gate PASS: handoff $HANDOFF_PATH has $PRESENT/$REQUIRED sections"
exit 0
