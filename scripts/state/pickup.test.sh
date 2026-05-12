#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
TRANS="$ARCGENTIC_ROOT/scripts/state/transition.sh"
PICKUP="$ARCGENTIC_ROOT/scripts/state/pickup.sh"

describe "pickup.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"

it "emits 'intake' for fresh state"
run bash "$PICKUP" --state-file "$SF"
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "intake"
assert_contains "$__LAST_OUTPUT" "planning"  # next state hint

it "emits role hint for planning state"
bash "$TRANS" --state-file "$SF" --target "planning" --by "test"
run bash "$PICKUP" --state-file "$SF"
assert_contains "$__LAST_OUTPUT" "planner"
assert_contains "$__LAST_OUTPUT" "handoff"

it "emits role hint for dev_in_progress state"
bash "$TRANS" --state-file "$SF" --target "awaiting_dev_start" --by "test" --skip-gates
bash "$TRANS" --state-file "$SF" --target "dev_in_progress" --by "test"
run bash "$PICKUP" --state-file "$SF"
assert_contains "$__LAST_OUTPUT" "developer"

it "emits role hint for audit_in_progress state"
bash "$TRANS" --state-file "$SF" --target "awaiting_audit" --by "test" --skip-gates
bash "$TRANS" --state-file "$SF" --target "audit_in_progress" --by "test"
run bash "$PICKUP" --state-file "$SF"
assert_contains "$__LAST_OUTPUT" "auditor"
assert_contains "$__LAST_OUTPUT" "verdict"

it "--json emits structured JSON"
run bash "$PICKUP" --state-file "$SF" --json
assert_contains "$__LAST_OUTPUT" '"current_state"'
assert_contains "$__LAST_OUTPUT" '"role"'

teardown_tmpdir
summary
