# arcgentic forward-debt registry

Tracking known limitations deferred to future rounds.

Format: `| ID | Severity | Description | Owner-round |`

## Active

| ID | Severity | Description | Owner-round |
|---|---|---|---|
| ER-RETRY | P2 | execute-round skill lacks retry-with-context loops (spec § 4.2.4); fail-fast on first sub-agent error. Re-invoke manually after fix. | v0.3 |
| ER-AUDIT-FACTS-RICH | P3 | execute-round self-audit now has an audit-check-backed fact table, but rich commit-chain / changed-file fact generation remains future work. | v0.3 |
| ER-STATE-ROW | P3 | execute-round Phase 1 CLAUDE.md state-row update is NO-OP (project-agnostic); project-specific hooks can override. | v0.3+ |

## Resolved

| ID | Resolved in | Evidence |
|---|---|---|
| ER-AUDIT-GATE-4 | v0.2.2-alpha.1 | execute-round Phase 4 writes self-audit handoff and runs `audit_check.run(..., strict_extended=True)` |
| ER-AUDIT-FACTS | v0.2.2-alpha.1 | self-audit § 7 no longer uses TODO placeholders; rich fact generation tracked separately as ER-AUDIT-FACTS-RICH |
| R1-CLOSEOUT-SEAM | R2-v1-release-hardening | `arcgentic close-round` anchors PASS verdicts, runs verdict completeness + strict audit-check, runs the lesson scan, transitions `passed -> closed`, and records `last_passed_round` |
| R1-SESSION-PROMPT-ROLE | R2-v1-release-hardening | `arcgentic session-mode prompt` accepts `--role developer\|auditor\|closeout`, and project-level `project.session_mode` suppresses per-round re-asking |
| R2-SELF-AUDIT-MUTABLE-FACTS | R3-v1-prepublish-fix | Generated self-audit facts now use stable artifact/fixed-anchor checks and tests cover re-running after synthetic HEAD advancement; template guidance bans current-state and moving-HEAD equality facts |
| R2-CODIFY-LESSON-PRECISION | R3-v1-prepublish-fix | `scan_last_n_rounds` now extracts only structured findings rows, ignores R2-style forward-debt prose, and tests preserve real repeated structured finding promotion |
