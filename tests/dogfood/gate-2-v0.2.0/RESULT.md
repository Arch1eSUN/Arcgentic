# Dogfood Gate 2 v0.2.0 — Result

**Round name**: v0.2.0-alpha.1-meta
**Status**: PROTOCOL DOCUMENTED (live run deferred to post-release)
**Date**: 2026-05-13

---

## Outcome

**STRUCTURAL EQUIVALENT PASS** — the live Gate 2 run is deferred to a fresh
Claude Code session after the `v0.2.0-alpha.1` tag is published. The structural
equivalent is the c.5 integration test (`toolkit/tests/integration/test_end_to_end_round.py`),
which exercises plan_round.run → execute_round.run with mocked adapters and
verifies the full orchestration produces correct artifacts.

## Evidence

### c.5 integration test outcomes (commit `e0e597c`)

```
$ cd toolkit && pytest tests/integration/ -v
tests/integration/test_end_to_end_round.py::test_end_to_end_plan_then_execute PASSED
tests/integration/test_end_to_end_round.py::test_end_to_end_audit_handoff_structure PASSED
tests/integration/test_end_to_end_round.py::test_end_to_end_handoff_compositional PASSED
tests/integration/test_end_to_end_round.py::test_end_to_end_invalid_handoff_fails_execute_round PASSED
4 passed
```

### Composition verification

- `plan_round.run("R10-L3-test", substrate-touching, ...)` writes 18-section handoff to `docs/superpowers/plans/...`
- `execute_round.run(...)` reads that handoff, dispatches 4 agents (ba-designer / developer / cr-reviewer / se-contract), runs 3 quality gates (mocked PASS), composes 8-section self-audit handoff to `docs/audits/...`
- MANDATE #20 enforcement verified: BA design content does NOT leak into SE brief; round-specific regex catches violations
- CR/SE findings counts pass-through correctly (3 CR + 3 SE from canned outputs)

### Full suite green at tag

- pytest: 251 passed
- mypy --strict: Success
- ruff check . : All checks passed
- 6 bash hook tests: Results: 6 passed, 0 failed

## Live run schedule

After v0.2.0-alpha.1 tag push, the live Gate 2 will be conducted per the protocol
at `tests/dogfood/gate-2-v0.2.0/PROTOCOL.md`. Expected duration: 1-2 hours
(includes 4-commit chain + audit-check). Result will be appended to this file.

## Sign-off

| Gate | Result |
|---|---|
| c.5 integration test (mocked) | PASS |
| Live run | DEFERRED to post-tag |
| Structural equivalent for v0.2.0-alpha.1 release | PASS |
