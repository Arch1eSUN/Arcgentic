#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
TRANS="$ARCGENTIC_ROOT/scripts/state/transition.sh"

describe "transition.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"

it "transitions intake → planning (no gate)"
run bash "$TRANS" --state-file "$SF" --target "planning" --by "test"
assert_eq "$__LAST_EXIT" 0
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"
CUR=$(yaml_get "$SF" "current_round.state")
assert_eq "$CUR" "planning"

it "rejects illegal transition planning → closed"
run bash "$TRANS" --state-file "$SF" --target "closed" --by "test"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "not allowed"

it "refuses transition with gate when --skip-gates absent"
# planning → awaiting_dev_start has handoff-doc-gate.sh which doesn't exist yet at this point
# (it will be Task 8). So we expect the gate-required transition to refuse.
run bash "$TRANS" --state-file "$SF" --target "awaiting_dev_start" --by "test"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "gate"

it "allows gated transition with --skip-gates"
run bash "$TRANS" --state-file "$SF" --target "awaiting_dev_start" --by "test" --skip-gates
assert_eq "$__LAST_EXIT" 0
CUR=$(yaml_get "$SF" "current_round.state")
assert_eq "$CUR" "awaiting_dev_start"

it "appends to state_history"
HIST=$(yaml_get "$SF" "current_round.state_history")
assert_contains "$HIST" "planning"
assert_contains "$HIST" "awaiting_dev_start"

teardown_tmpdir
summary
