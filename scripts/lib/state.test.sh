#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"
source "$ARCGENTIC_ROOT/scripts/lib/state.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"

describe "state.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"

it "state_current_value reads the current state"
VAL=$(state_current_value "$SF")
assert_eq "$VAL" "intake"

it "state_allowed_next returns the legal next states"
NEXT=$(state_allowed_next "$SF")
assert_contains "$NEXT" "planning"

it "state_is_transition_allowed approves a legal transition"
run state_is_transition_allowed "$SF" "planning"
assert_eq "$__LAST_EXIT" 0

it "state_is_transition_allowed rejects an illegal transition"
run state_is_transition_allowed "$SF" "closed"
assert_neq "$__LAST_EXIT" 0

it "state_required_gate returns gate when source state has one"
yaml_set "$SF" "current_round.state" "planning"
GATE=$(state_required_gate "$SF" "awaiting_dev_start")
assert_eq "$GATE" "handoff-doc-gate.sh"

it "state_required_gate returns empty when source state has no gate"
yaml_set "$SF" "current_round.state" "awaiting_dev_start"
GATE=$(state_required_gate "$SF" "dev_in_progress")
assert_eq "$GATE" ""

teardown_tmpdir
summary
