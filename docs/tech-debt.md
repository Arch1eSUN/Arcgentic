# arcgentic forward-debt registry

Tracking known limitations deferred to future rounds.

Format: `| ID | Severity | Description | Owner-round |`

## Active

| ID | Severity | Description | Owner-round |
|---|---|---|---|
| ER-RETRY | P2 | execute-round skill lacks retry-with-context loops (spec § 4.2.4); fail-fast on first sub-agent error. Re-invoke manually after fix. | v0.2.1 |
| ER-AUDIT-GATE-4 | P1 | execute-round skill skips quality gate 4 (audit-check); integrates once audit_check.py ships in sub-phase d.1. | v0.2.0 d.1 |
| ER-AUDIT-FACTS | P2 | execute-round's self-audit § 7 mechanical fact table is skeletoned with TODO markers; auto-generation pending audit-check integration. | v0.2.0 d.1 |
| ER-STATE-ROW | P3 | execute-round Phase 1 CLAUDE.md state-row update is NO-OP (project-agnostic); project-specific hooks can override. | v0.3+ |

## Resolved

(empty — first arcgentic round)
