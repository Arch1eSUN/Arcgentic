#!/opt/homebrew/bin/bash
# pre-commit-fact-check.test.sh — tests for .githooks/pre-commit
# Requires bash 4+ (mapfile). Uses /opt/homebrew/bin/bash shebang.
# Exit non-zero on any test failure.

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HOOK="$REPO_ROOT/.githooks/pre-commit"

if [ ! -x "$HOOK" ]; then
    echo "FAIL: hook not executable at $HOOK"
    exit 1
fi

PASSED=0
FAILED=0
ISOLATED_DIR=""
ORIG_PATH=""

_run_test() {
    local name="$1"
    local test_fn="$2"
    if $test_fn; then
        echo "PASS: $name"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL: $name"
        FAILED=$((FAILED + 1))
    fi
}

# Helper: create an isolated git repo.
# Sets ISOLATED_DIR and ORIG_PATH globals; prepends stub-bin to PATH.
# Caller must call _cleanup_isolated_repo after.
_setup_isolated_repo() {
    ISOLATED_DIR=$(mktemp -d)
    ORIG_PATH="$PATH"
    pushd "$ISOLATED_DIR" > /dev/null
    git init -q
    git config user.email "test@test"
    git config user.name "Test"
    mkdir -p docs/audits
    # Stub arcgentic CLI — exit code controlled by STUB_ARCGENTIC_EXIT (default 0)
    mkdir -p stub-bin
    cat > stub-bin/arcgentic <<'EOF'
#!/usr/bin/env bash
# Stub arcgentic CLI for hook tests.
exit "${STUB_ARCGENTIC_EXIT:-0}"
EOF
    chmod +x stub-bin/arcgentic
    # Prepend stub-bin to PATH so hook finds stub over real arcgentic
    export PATH="$ISOLATED_DIR/stub-bin:$PATH"
}

_cleanup_isolated_repo() {
    popd > /dev/null 2>&1 || true
    export PATH="$ORIG_PATH"
    rm -rf "$ISOLATED_DIR"
}

# Test 1: no staged audits → exit 0
test_no_staged_audits() {
    _setup_isolated_repo
    echo "hello" > README.md
    git add README.md
    local rc=0
    "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 0 ]
}

# Test 2: staged non-audit file → exit 0
test_staged_non_audit() {
    _setup_isolated_repo
    echo "code" > src.py
    git add src.py
    local rc=0
    "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 0 ]
}

# Test 3: staged audit handoff with PASSING audit-check → exit 0
test_audit_handoff_passes() {
    _setup_isolated_repo
    echo "# audit" > docs/audits/R1.0.md
    git add docs/audits/R1.0.md
    # Stub exits 0 by default
    local rc=0
    "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 0 ]
}

# Test 4: staged audit handoff with FAILING audit-check → exit 1
test_audit_handoff_fails() {
    _setup_isolated_repo
    echo "# audit" > docs/audits/R1.0.md
    git add docs/audits/R1.0.md
    # Stub exits 1 → hook must exit 1
    local rc=0
    STUB_ARCGENTIC_EXIT=1 "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 1 ]
}

# Test 5: external-audit-verdict.md is excluded → exit 0 even with failing arcgentic
test_external_verdict_excluded() {
    _setup_isolated_repo
    echo "# verdict" > docs/audits/R1.0-external-audit-verdict.md
    git add docs/audits/R1.0-external-audit-verdict.md
    # Stub exits 1; but hook should exit 0 because file is excluded
    local rc=0
    STUB_ARCGENTIC_EXIT=1 "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 0 ]
}

# Test 6: arcgentic CLI missing → exit 1
test_arcgentic_missing() {
    _setup_isolated_repo
    echo "# audit" > docs/audits/R1.0.md
    git add docs/audits/R1.0.md
    # Build a PATH that has git + homebrew (so hook shebang works and git works)
    # but excludes stub-bin and any real arcgentic install (e.g. /opt/anaconda3/bin).
    # Strategy: use ORIG_PATH (before stub-bin was prepended) and strip anaconda.
    local no_arcgentic_path
    no_arcgentic_path=$(echo "$ORIG_PATH" \
        | tr ':' '\n' \
        | grep -v '/anaconda' \
        | grep -v '/stub-bin' \
        | tr '\n' ':' \
        | sed 's/:$//')
    local rc=0
    PATH="$no_arcgentic_path" "$HOOK" || rc=$?
    _cleanup_isolated_repo
    [ "$rc" -eq 1 ]
}

# Run all tests
_run_test "no staged audits → exit 0" test_no_staged_audits
_run_test "staged non-audit file → exit 0" test_staged_non_audit
_run_test "audit handoff passes → exit 0" test_audit_handoff_passes
_run_test "audit handoff fails → exit 1" test_audit_handoff_fails
_run_test "external-verdict excluded → exit 0" test_external_verdict_excluded
_run_test "arcgentic missing → exit 1" test_arcgentic_missing

echo ""
echo "Results: $PASSED passed, $FAILED failed"
if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
exit 0
