#!/usr/bin/env bash
# scripts/test-helpers.sh — shared Bash test framework for arcgentic.
# Sourced by every *.test.sh. Pure Bash, no external deps.
#
# Test file pattern:
#   #!/usr/bin/env bash
#   source "$(dirname "$0")/../test-helpers.sh"
#   describe "init.sh"
#   it "creates state.yaml when missing"
#   setup_tmpdir
#   run bash "$ARCGENTIC_ROOT/scripts/state/init.sh" "$TMPDIR"
#   assert_eq "$__LAST_EXIT" 0
#   assert_file_exists "$TMPDIR/.agentic-rounds/state.yaml"
#   teardown_tmpdir
#   summary

set -uo pipefail

ARCGENTIC_ROOT="${ARCGENTIC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export ARCGENTIC_ROOT

__TESTS_RUN=0
__TESTS_FAIL=0
__CURRENT_TEST=""

if [ -t 1 ]; then
  GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; NC=''
fi

describe() { printf "\n%bdescribe%b %s\n" "$YELLOW" "$NC" "$1"; }
it() { __CURRENT_TEST="$1"; __TESTS_RUN=$((__TESTS_RUN+1)); }

__pass() { printf "  %b✓%b %s\n" "$GREEN" "$NC" "$__CURRENT_TEST"; }
__fail() {
  __TESTS_FAIL=$((__TESTS_FAIL+1))
  printf "  %b✗%b %s\n      %s\n" "$RED" "$NC" "$__CURRENT_TEST" "$1"
}

assert_eq() {
  if [ "$1" = "$2" ]; then __pass; else __fail "expected '$2', got '$1'"; fi
}
assert_neq() {
  if [ "$1" != "$2" ]; then __pass; else __fail "expected != '$2', got '$1'"; fi
}
assert_contains() {
  if printf "%s" "$1" | grep -qF -- "$2"; then __pass; else __fail "missing '$2' in: $1"; fi
}
assert_not_contains() {
  if printf "%s" "$1" | grep -qF -- "$2"; then __fail "unexpected '$2' in: $1"; else __pass; fi
}
assert_file_exists() {
  if [ -f "$1" ]; then __pass; else __fail "file missing: $1"; fi
}
assert_file_not_exists() {
  if [ ! -f "$1" ]; then __pass; else __fail "file unexpectedly present: $1"; fi
}

setup_tmpdir() {
  TMPDIR=$(mktemp -d -t arcgentic-test-XXXXXX)
  export TMPDIR
}
teardown_tmpdir() {
  [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ] && rm -rf "$TMPDIR"
  unset TMPDIR
}

run() {
  __LAST_OUTPUT="$("$@" 2>&1)"
  __LAST_EXIT=$?
  export __LAST_OUTPUT __LAST_EXIT
  return $__LAST_EXIT
}

summary() {
  local pass=$((__TESTS_RUN - __TESTS_FAIL))
  if [ $__TESTS_FAIL -eq 0 ]; then
    printf "\n%b%d passing%b (%d total)\n" "$GREEN" "$pass" "$NC" "$__TESTS_RUN"
    exit 0
  else
    printf "\n%b%d failing%b (%d total)\n" "$RED" "$__TESTS_FAIL" "$NC" "$__TESTS_RUN"
    exit 1
  fi
}
