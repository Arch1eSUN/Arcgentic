#!/usr/bin/env bash
# scripts/state/init.test.sh
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"

describe "init.sh"

it "creates .agentic-rounds/state.yaml when missing"
setup_tmpdir
run bash "$INIT" --project-root "$TMPDIR" --project-name "test-proj" --round-naming "phase.round"
assert_eq "$__LAST_EXIT" 0
assert_file_exists "$TMPDIR/.agentic-rounds/state.yaml"

it "refuses to overwrite an existing state.yaml without --force"
run bash "$INIT" --project-root "$TMPDIR" --project-name "test-proj" --round-naming "phase.round"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "already exists"

it "overwrites with --force"
run bash "$INIT" --project-root "$TMPDIR" --project-name "test-proj-2" --round-naming "sprint.story" --force
assert_eq "$__LAST_EXIT" 0
# verify it actually changed
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"
NAME=$(yaml_get "$TMPDIR/.agentic-rounds/state.yaml" "project.name")
assert_eq "$NAME" "test-proj-2"
teardown_tmpdir

it "fails clearly when --project-root missing"
run bash "$INIT" --project-name "x" --round-naming "y"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "--project-root"

summary
