#!/usr/bin/env bash
# scripts/lib/state.sh — state-machine helper functions.
# Sourced by transition.sh / pickup.sh / gate scripts.
# Requires scripts/lib/yaml.sh to be sourced first.

set -uo pipefail

# Read the current state value from state.yaml.
# Usage: state_current_value STATE_FILE
state_current_value() {
  yaml_get "$1" "current_round.state"
}

# Read the allowed next states (as space-separated string).
# Usage: state_allowed_next STATE_FILE
state_allowed_next() {
  local sf="$1"
  local cur
  cur=$(state_current_value "$sf")
  # The `next` field is a list — yaml_get returns it as JSON. Parse with Python.
  python3 - "$sf" "$cur" <<'PY'
import sys, yaml
sf, cur = sys.argv[1], sys.argv[2]
with open(sf) as f:
    data = yaml.safe_load(f) or {}
states = data.get("states", {})
if cur not in states:
    sys.exit(0)
nxt = states[cur].get("next", []) or []
print(" ".join(nxt))
PY
}

# Exit 0 if transition from current state to TARGET is allowed.
# Usage: state_is_transition_allowed STATE_FILE TARGET
state_is_transition_allowed() {
  local sf="$1" target="$2"
  local allowed
  allowed=$(state_allowed_next "$sf")
  for a in $allowed; do
    if [ "$a" = "$target" ]; then
      return 0
    fi
  done
  return 1
}

# Return the gate script name required for a transition (or empty).
# Usage: state_required_gate STATE_FILE TARGET
state_required_gate() {
  local sf="$1" target="$2"
  python3 - "$sf" "$target" <<'PY'
import sys, yaml
sf, target = sys.argv[1], sys.argv[2]
with open(sf) as f:
    data = yaml.safe_load(f) or {}
states = data.get("states", {})
# The gate is attached to the SOURCE state, not the target,
# but applies for any transition. We surface the source's gate
# only if the target is among its `next`.
cur_state = data.get("current_round", {}).get("state", "")
src = states.get(cur_state, {})
if target in (src.get("next") or []):
    print(src.get("gate") or "")
PY
}

# Append a state_history entry. Caller is responsible for state validity.
# Usage: state_append_history STATE_FILE NEW_STATE BY [ARTIFACT]
state_append_history() {
  local sf="$1" new_state="$2" by="$3" artifact="${4:-}"
  local ts entry
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -n "$artifact" ]; then
    entry=$(printf '{"state":"%s","ts":"%s","by":"%s","artifact":"%s"}' "$new_state" "$ts" "$by" "$artifact")
  else
    entry=$(printf '{"state":"%s","ts":"%s","by":"%s"}' "$new_state" "$ts" "$by")
  fi
  yaml_append_to_list "$sf" "current_round.state_history" "$entry"
}
