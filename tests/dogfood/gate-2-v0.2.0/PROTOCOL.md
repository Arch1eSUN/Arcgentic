# Dogfood Gate 2 — v0.2.0-alpha.1-meta round protocol

**Round name**: `v0.2.0-alpha.1-meta`
**Round type**: `entry-admin` (governance round; no substrate code)
**Status**: PROTOCOL DOCUMENTED; live run scheduled for post-release.

---

## Purpose

Gate 2 verifies arcgentic can ship arcgentic itself — that `plan-round` skill +
`execute-round` skill compose end-to-end on the very repo they were built in.
Prior precedent: v0.1.0-alpha.2-meta round at
`tests/dogfood/gate-2-live-run/RESULT.md`.

## Why deferred to post-release

The live run requires actually dispatching Claude Code Task tool from inside a
running Claude Code session — which means execution from a NEW Claude Code session
after the v0.2.0-alpha.1 tag is published. The current build session committed
all v0.2.0-alpha.1 deliverables; the dogfood run is the next step.

The integration test at `toolkit/tests/integration/test_end_to_end_round.py`
(c.5) verifies the plan_round → execute_round composition with mocked adapters
+ 4 e2e tests. This is the "structural Gate 2 equivalent" — proves the wiring
is sound. The live Gate 2 is the validation that real Claude Code dispatch
behaves as designed.

## Live-run protocol (when executed)

1. Pull v0.2.0-alpha.1 tag fresh into a new Claude Code session
2. Install toolkit: `cd toolkit && pip install -e ".[dev]"`
3. Verify `arcgentic --version` works
4. Verify `arcgentic audit-check tests/fixtures/sample_self_audit.md` produces expected output
5. Invoke `/plan-round v0.2.0-alpha.1-meta entry-admin <PRIOR_ANCHOR> "Document v0.2.0 close + open v0.2.1"`
6. Verify handoff written to `docs/superpowers/plans/{date}-v0.2.0-alpha.1-meta-handoff.md`
7. Invoke `/execute-round v0.2.0-alpha.1-meta`
8. Verify 4-commit chain landed; self-audit handoff at `docs/audits/v0.2.0-alpha.1-meta.md`
9. Run `arcgentic audit-check docs/audits/v0.2.0-alpha.1-meta.md --strict-extended`
10. Record outcome in `RESULT.md` (PASS / NEEDS_FIX with details)

## Pass criteria

- All 4 phases of execute-round produce commits
- Self-audit handoff has 8 § sections per spec § 9
- audit-check passes (N/N + AC-1 + AC-3 clean)
- No MANDATE #20 violation (SE brief contains no `{ROUND_UPPER}_BA_DESIGN` marker)
- Quality gates 1-3 (mypy / pytest / ruff) PASS; gate 4 may SKIP or PASS

## Anti-scope

Not in this gate:
- Cross-project portability (Gate 3 territory)
- Performance benchmarks
- Multi-IDE adapter validation (Cursor / Codex CLI live runs)

## Sign-off

| Item | Status |
|---|---|
| Integration test (mocked) passes | ✅ c.5 (commit `e0e597c`) |
| Live run | ⏳ Post-tag |
| Result documented | ⏳ Post-tag |
