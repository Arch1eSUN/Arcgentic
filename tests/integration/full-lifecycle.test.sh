#!/usr/bin/env bash
# tests/integration/full-lifecycle.test.sh — end-to-end state machine.
# Walks intake → planning → awaiting_dev_start → dev_in_progress → awaiting_audit
# → audit_in_progress → passed → closed, with all gates satisfied.

source "$(dirname "$0")/../../scripts/test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
TRANS="$ARCGENTIC_ROOT/scripts/state/transition.sh"
PICKUP="$ARCGENTIC_ROOT/scripts/state/pickup.sh"
VALIDATE="$ARCGENTIC_ROOT/scripts/state/validate-schema.sh"

describe "full-lifecycle (intake → closed)"

setup_tmpdir
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"

# Initialize
bash "$INIT" --project-root "$TMPDIR" --project-name "lifecycle" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"

# Set up project git repo + verdict file + handoff file dirs
( cd "$TMPDIR" && git init -q -b main && git config user.email t@t.t && git config user.name t )
mkdir -p "$TMPDIR/docs/plans" "$TMPDIR/docs/audits"

it "schema-validates after init"
run bash "$VALIDATE" "$SF"
assert_eq "$__LAST_EXIT" 0

it "intake → planning (no gate)"
run bash "$TRANS" --state-file "$SF" --target "planning" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "planning → awaiting_dev_start (handoff-doc-gate)"
# Write a handoff doc
echo "# Handoff" > "$TMPDIR/docs/plans/round-1.md"
yaml_set "$SF" "current_round.handoff_doc" '{"path":"docs/plans/round-1.md","commit":"0000000","sections_present":16,"sections_required":16}'
run bash "$TRANS" --state-file "$SF" --target "awaiting_dev_start" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "awaiting_dev_start → dev_in_progress (no gate)"
run bash "$TRANS" --state-file "$SF" --target "dev_in_progress" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "dev_in_progress → awaiting_audit (round-commit-chain-gate)"
# Create 4 commits in the project repo
for i in 1 2 3 4; do
  ( cd "$TMPDIR" && echo "$i" > "f$i" && git add . && git commit -q -m "round-1 commit $i" )
done
COMMITS=$(cd "$TMPDIR" && git log --format=%H | head -4)
JSON_LIST=$(printf '"%s",' $COMMITS | sed 's/,$//')
yaml_set "$SF" "current_round.expected_dev_commits" "4"
yaml_set "$SF" "current_round.dev_commits" "[$JSON_LIST]"
run bash "$TRANS" --state-file "$SF" --target "awaiting_audit" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "awaiting_audit → audit_in_progress (no gate)"
run bash "$TRANS" --state-file "$SF" --target "audit_in_progress" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "audit_in_progress → passed (verdict-fact-table-gate)"
echo "# Verdict PASS" > "$TMPDIR/docs/audits/v1.md"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/v1.md","commit":"0000001","outcome":"PASS","fact_table_total":15,"fact_table_pass":15,"findings":[]}'
run bash "$TRANS" --state-file "$SF" --target "passed" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "passed → closed (no gate)"
run bash "$TRANS" --state-file "$SF" --target "closed" --by "lifecycle-test"
assert_eq "$__LAST_EXIT" 0

it "state history records all 8 transitions"
HIST=$(yaml_get "$SF" "current_round.state_history")
for s in planning awaiting_dev_start dev_in_progress awaiting_audit audit_in_progress passed closed; do
  assert_contains "$HIST" "$s"
done

it "schema-validates after full lifecycle"
run bash "$VALIDATE" "$SF"
assert_eq "$__LAST_EXIT" 0

it "pickup emits 'closed' state guidance"
run bash "$PICKUP" --state-file "$SF"
assert_contains "$__LAST_OUTPUT" "closed"

teardown_tmpdir
summary
