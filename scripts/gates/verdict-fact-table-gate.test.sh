#!/usr/bin/env bash
source "$(dirname "$0")/../test-helpers.sh"

INIT="$ARCGENTIC_ROOT/scripts/state/init.sh"
GATE="$ARCGENTIC_ROOT/scripts/gates/verdict-fact-table-gate.sh"

describe "verdict-fact-table-gate.sh"

setup_tmpdir
bash "$INIT" --project-root "$TMPDIR" --project-name "t" --round-naming "phase.round"
SF="$TMPDIR/.agentic-rounds/state.yaml"
source "$ARCGENTIC_ROOT/scripts/lib/yaml.sh"

mkdir -p "$TMPDIR/docs/audits"

it "fails when audit_verdict not set"
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "audit_verdict"

it "fails when verdict file missing"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/missing.md","commit":"abc1234","outcome":"PASS","fact_table_total":10,"fact_table_pass":10}'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "not found"

it "fails when fact_table_pass < fact_table_total"
echo "verdict content" > "$TMPDIR/docs/audits/v.md"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/v.md","commit":"abc1234","outcome":"PASS","fact_table_total":10,"fact_table_pass":7}'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "7 < 10"

it "fails when outcome=PASS but findings has P0/P1"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/v.md","commit":"abc1234","outcome":"PASS","fact_table_total":10,"fact_table_pass":10,"findings":[{"id":"F-1","priority":"P1","summary":"blocker"}]}'
run bash "$GATE" --state-file "$SF"
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "P1"

it "passes when verdict file exists + facts all PASS + no P0/P1 findings"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/v.md","commit":"abc1234","outcome":"PASS","fact_table_total":10,"fact_table_pass":10,"findings":[{"id":"F-3","priority":"P3","summary":"informational"}]}'
run bash "$GATE" --state-file "$SF"
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "PASS"

it "passes for NEEDS_FIX outcome regardless of fact count (NEEDS_FIX is a legitimate transition)"
yaml_set "$SF" "current_round.audit_verdict" '{"path":"docs/audits/v.md","commit":"abc1234","outcome":"NEEDS_FIX","fact_table_total":10,"fact_table_pass":10,"findings":[{"id":"F-1","priority":"P1","summary":"real issue"}]}'
run bash "$GATE" --state-file "$SF"
assert_eq "$__LAST_EXIT" 0

teardown_tmpdir
summary
