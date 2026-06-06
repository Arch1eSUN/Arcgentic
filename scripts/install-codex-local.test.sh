#!/usr/bin/env bash
source "$(dirname "$0")/test-helpers.sh"

INSTALL="$ARCGENTIC_ROOT/scripts/install-codex-local.sh"

describe "install-codex-local.sh"

it "creates a local plugin symlink and marketplace entry"
setup_tmpdir
run bash "$INSTALL" --plugin-root "$ARCGENTIC_ROOT" --home "$TMPDIR" --skip-validate
assert_eq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "arcgentic Codex local plugin installed"
if [ -L "$TMPDIR/plugins/arcgentic" ]; then
  __pass
else
  __fail "plugin symlink missing"
fi
assert_file_exists "$TMPDIR/plugins/.agents/plugins/marketplace.json"
assert_contains "$(cat "$TMPDIR/plugins/.agents/plugins/marketplace.json")" '"path": "./arcgentic"'
teardown_tmpdir

it "refuses to replace a non-symlink install path"
setup_tmpdir
mkdir -p "$TMPDIR/plugins/arcgentic"
run bash "$INSTALL" --plugin-root "$ARCGENTIC_ROOT" --home "$TMPDIR" --skip-validate
assert_neq "$__LAST_EXIT" 0
assert_contains "$__LAST_OUTPUT" "Refusing to replace non-symlink path"
teardown_tmpdir

summary
