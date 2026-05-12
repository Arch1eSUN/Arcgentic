#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
GATE="$ARCGENTIC_ROOT/scripts/gates/round-commit-chain-gate.sh"

describe "round-commit-chain-gate.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"

# Set up a git repo with some commits in $TMPDIR
( cd "$TMPDIR" && git init -q -b main && git config user.email t@t.t && git config user.name t )
for i in 1 2 3 4; do
  ( cd "$TMPDIR" && echo "$i" > "f$i" && git add . && git commit -q -m "commit $i" )
done

it "fails when expected_dev_commits not set"
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "expected_dev_commits"

it "fails when dev_commits count < expected"
yaml_set "$SF" "current_round.expected_dev_commits" "4"
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "0 < 4"

it "fails when a listed commit doesn't exist in git"
yaml_set "$SF" "current_round.dev_commits" '["deadbeef","cafebabe","beefcafe","faceface"]'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "deadbeef"

it "passes when all commits valid + count matches"
COMMITS=$(cd "$TMPDIR" && git log --format=%H | head -4)
JSON_LIST=$(printf '"%s",' $COMMITS | sed 's/,$//')
yaml_set "$SF" "current_round.dev_commits" "[$JSON_LIST]"
run bash "$GATE" --state-file "$SF"
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "PASS"

teardown_tmpdir
summary
