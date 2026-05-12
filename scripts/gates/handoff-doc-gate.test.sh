#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
GATE="$ARCGENTIC_ROOT/scripts/gates/handoff-doc-gate.sh"

describe "handoff-doc-gate.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"

it "fails when handoff_doc.path not set"
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "handoff_doc.path"

it "fails when handoff_doc file does not exist"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"
yaml_set "$SF" "current_round.handoff_doc" '{"path":"docs/plans/missing.md","commit":"abc1234","sections_present":16,"sections_required":16}'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "not found"

it "fails when sections_present < sections_required"
mkdir -p "$TMPDIR/docs/plans"
echo "# Handoff" > "$TMPDIR/docs/plans/test.md"
yaml_set "$SF" "current_round.handoff_doc" '{"path":"docs/plans/test.md","commit":"abc1234","sections_present":10,"sections_required":16}'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "10 < 16"

it "passes when handoff_doc exists + sections complete"
yaml_set "$SF" "current_round.handoff_doc" '{"path":"docs/plans/test.md","commit":"abc1234","sections_present":16,"sections_required":16}'
run bash "$GATE" --state-file "$SF"
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "PASS"

teardown_tmpdir
summary
