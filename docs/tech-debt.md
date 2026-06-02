# arcgentic forward-debt registry

Tracking known limitations deferred to future rounds.

Format: `| ID | Severity | Description | Owner-round |`

## Active

| ID | Severity | Description | Owner-round |
|---|---|---|---|
| ER-RETRY | P2 | execute-round skill lacks retry-with-context loops (spec § 4.2.4); fail-fast on first sub-agent error. Re-invoke manually after fix. | v0.3 |
| ER-AUDIT-FACTS-RICH | P3 | execute-round self-audit now has an audit-check-backed fact table, but rich commit-chain / changed-file fact generation remains future work. | v0.3 |
| ER-STATE-ROW | P3 | execute-round Phase 1 CLAUDE.md state-row update is NO-OP (project-agnostic); project-specific hooks can override. | v0.3+ |
| R1-CLOSEOUT-SEAM | P1 | R1 PASS exposed a lifecycle gap: after external audit passes, arcgentic does not provide a first-class closeout command that anchors the verdict, codifies lessons, transitions `passed -> closed`, and emits the next-round handoff. | v1.0.0 release hardening |
| R1-SESSION-PROMPT-ROLE | P2 | `session-mode prompt --mode multi-session` prints the developer prompt first and lacks an explicit `--role developer\|auditor` selector. | v1.0.0 release hardening |

## Resolved

| ID | Resolved in | Evidence |
|---|---|---|
| ER-AUDIT-GATE-4 | v0.2.2-alpha.1 | execute-round Phase 4 writes self-audit handoff and runs `audit_check.run(..., strict_extended=True)` |
| ER-AUDIT-FACTS | v0.2.2-alpha.1 | self-audit § 7 no longer uses TODO placeholders; rich fact generation tracked separately as ER-AUDIT-FACTS-RICH |
