# arcgentic forward-debt registry

Tracking known limitations deferred to future rounds.

Format: `| ID | Severity | Description | Owner-round |`

## Active

| ID | Severity | Description | Owner-round |
|---|---|---|---|
| ER-RETRY | P2 | execute-round skill lacks retry-with-context loops (spec § 4.2.4); fail-fast on first sub-agent error. Re-invoke manually after fix. | v0.3 |
| ER-AUDIT-FACTS-RICH | P3 | execute-round self-audit now has an audit-check-backed fact table, but rich commit-chain / changed-file fact generation remains future work. | v0.3 |
| ER-STATE-ROW | P3 | execute-round Phase 1 CLAUDE.md state-row update is NO-OP (project-agnostic); project-specific hooks can override. | v0.3+ |
| R2-SELF-AUDIT-MUTABLE-FACTS | P2 | Developer self-audit facts should not assert mutable current state or moving `HEAD`; use `state_history`, fixed commit anchors, or artifact existence checks so external audit and closeout can rerun them after transitions. | v1.0.1 |
| R2-CODIFY-LESSON-PRECISION | P2 | `close-round` dogfood generated a noisy lesson/amendment slug (`future-fact-audit-state-both`) by clustering broad audit text; codify-lesson should cluster structured finding IDs/summaries instead of unrelated verdict prose. | v1.0.1 |

## Resolved

| ID | Resolved in | Evidence |
|---|---|---|
| ER-AUDIT-GATE-4 | v0.2.2-alpha.1 | execute-round Phase 4 writes self-audit handoff and runs `audit_check.run(..., strict_extended=True)` |
| ER-AUDIT-FACTS | v0.2.2-alpha.1 | self-audit § 7 no longer uses TODO placeholders; rich fact generation tracked separately as ER-AUDIT-FACTS-RICH |
| R1-CLOSEOUT-SEAM | R2-v1-release-hardening | `arcgentic close-round` anchors PASS verdicts, runs verdict completeness + strict audit-check, runs the lesson scan, transitions `passed -> closed`, and records `last_passed_round` |
| R1-SESSION-PROMPT-ROLE | R2-v1-release-hardening | `arcgentic session-mode prompt` accepts `--role developer\|auditor\|closeout`, and project-level `project.session_mode` suppresses per-round re-asking |
