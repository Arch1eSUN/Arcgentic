#!/usr/bin/env bash
# scripts/gates/round-commit-chain-gate.sh — dev_in_progress → awaiting_audit gate.
#
# Passes iff:
#   current_round.expected_dev_commits is set + > 0
#   current_round.dev_commits has length >= expected_dev_commits
#   every commit hash resolves in the project's git repo

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
EXPECTED=$(yaml_get "$STATE_FILE" "current_round.expected_dev_commits")
COMMITS_JSON=$(yaml_get "$STATE_FILE" "current_round.dev_commits")

if [ -z "$EXPECTED" ] || [ "$EXPECTED" -lt 1 ]; then
  echo "Gate FAIL: expected_dev_commits not set or < 1" >&2
  exit 1
fi

# Parse commit list via Python
ACTUAL_COUNT=$(python3 -c "import json,sys; d=json.loads(sys.argv[1] or '[]'); print(len(d))" "${COMMITS_JSON:-[]}")
if [ "$ACTUAL_COUNT" -lt "$EXPECTED" ]; then
  echo "Gate FAIL: dev_commits count $ACTUAL_COUNT < $EXPECTED expected" >&2
  exit 1
fi

# Verify each commit exists
COMMITS=$(python3 -c "import json,sys; print(' '.join(json.loads(sys.argv[1])))" "$COMMITS_JSON")
for sha in $COMMITS; do
  if ! ( cd "$PROJECT_ROOT" && git cat-file -e "$sha" 2>/dev/null ); then
    echo "Gate FAIL: commit not found in repo: $sha" >&2
    exit 1
  fi
done

echo "Gate PASS: $ACTUAL_COUNT/$EXPECTED commits verified in $PROJECT_ROOT"
exit 0
