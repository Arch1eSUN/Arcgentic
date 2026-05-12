#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

VALIDATE="$ARCGENTIC_ROOT/scripts/state/validate-schema.sh"
INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"

describe "validate-schema.sh"

it "passes on a freshly-initialized state.yaml"
setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
run bash "$VALIDATE" "$TMPDIR/.agentic-rounds/state.yaml"
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "valid"

it "fails on a state.yaml missing required field"
# Truncate to remove the project section
sed -i.bak '/^project:/,/^current_round:/{/^current_round:/!d;}' "$TMPDIR/.agentic-rounds/state.yaml"
run bash "$VALIDATE" "$TMPDIR/.agentic-rounds/state.yaml"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "project"
teardown_tmpdir

it "fails with clear error if state.yaml missing"
setup_tmpdir
run bash "$VALIDATE" "$TMPDIR/does-not-exist.yaml"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "not found"
teardown_tmpdir

summary
