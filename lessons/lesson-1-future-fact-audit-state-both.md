---
lesson:
  id: 1
  slug: future-fact-audit-state-both
  status: FORMAL
  origin_round: R2-v1-release-hardening
  observed_count: 10
  preservation_streak: "0-of-0"
  novel_preservation_types_seen: []
  mandate_amendments_triggered: []
---

# Lesson 1: future fact audit state both

## Definition

Repeated audit pattern: future fact audit state both.

## Examples

  - R2-v1-release-hardening: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R2-v1-release-hardening.md:17 — D-R2-v1-release-hardening-1 P2 Self-audit facts #3 and #19 are historical current-state/current-HEAD facts, not stable re-audit facts. docs/audits/R2-v1-release-hardening-self-audit.md` fact #3 expects `awaiting_audit`; fact #19 expects current `HEAD` to equal the dev self-audit commit. Both become stale after valid audit/closeout commits. Self-audit facts intended for external rerun should remain stable after `awaiting_audit -> audit_in_progress` and after audit verdict commits, or explicitly verify state_history/fixed dev anchors. Current state has advanced past `awaiting_audit`, and current `HEAD` can advance beyond the dev commit while the state self-audit anchor remains valid. In a future cleanup, change developer self-audit state facts to verify state_history or self_audit_doc artifact instead of current mutable state/HEAD. Fact rows 3-4 document the raw failure and the stable replacement check.
  - R2-v1-release-hardening: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R2-v1-release-hardening.md:35 — 1 docs/audits/R1-v1-openspec-marketplace.md Carries the prior successful verdict and P2 role-selector debt R1 P2 prompt-role finding and fact-table shape No R1 verdict edits by developer
  - R2-v1-release-hardening: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R2-v1-release-hardening.md:80 — - D-R2-v1-release-hardening-1 (P2): make future self-audit state/HEAD facts stable across audit and closeout transitions by checking `state_history` and fixed dev anchors instead of current mutable state/HEAD.
  - R2-v1-release-hardening: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R2-v1-release-hardening.md:84 — The release-hardening work is cohesive and matches the R2 handoff. The one P2 is about audit fact durability across state and HEAD transitions, not product behavior. No P0/P1 blockers remain.
  - R1-v1-openspec-marketplace: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R1-v1-openspec-marketplace.md:17 — D-R1-v1-openspec-marketplace-1 P2 session-mode prompt --mode multi-session` still prints the developer prompt only. Fact row 19 returns first line `You are the arcgentic developer only for round R1-v1-openspec-marketplace. Non-blocking: recommendation JSON already exposes both identity prompts, and current handoff supplied the auditor prompt. CLI prompt subcommand does not directly select auditor identity. In a future UX cleanup, add an explicit `--role developer auditor` selector for `session-mode prompt`.
  - R1-v1-openspec-marketplace: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/R1-v1-openspec-marketplace.md:80 — - D-R1-v1-openspec-marketplace-1 (P2): `session-mode prompt --mode multi-session` should grow an explicit role selector in a future UX cleanup. It does not block this round because the required recommendation output contains both prompts and the actual audit handoff was explicit.
  - v0.2.2-alpha.1-external-audit-verdict: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/v0.2.2-alpha.1-external-audit-verdict.md:53 — **Residual risk**: Low. The skill doc and implementation now describe the same phase ownership. Richer fact generation remains tracked separately as `ER-AUDIT-FACTS-RICH` P3 forward-debt.
  - v0.1.0-alpha.2-meta-external-audit-verdict: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/v0.1.0-alpha.2-meta-external-audit-verdict.md:17 — F-v0.1.0-a2-meta-1 P3 README current-version block uses "13 reference docs" but plan checkpoint document claims 12 — minor narrative count consistency note. arcgentic README is correct (real count = 13); plan checkpoint had arithmetic typo "(1+1+8+3)=12" which actually equals 13. find skills/*/references -name '*.md' \ wc -l` → 13; plan checkpoint line "expect 12" is the source-of-truth typo, not the README.
  - v0.1.0-alpha.2-meta-external-audit-verdict: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/v0.1.0-alpha.2-meta-external-audit-verdict.md:60 — - D-v0.1.0-a2-meta-1 (P3): plan checkpoint section in `docs/plans/2026-05-12-arcgentic-mvp-plan.md` has arithmetic typo "expect 12 (1+1+8+3)" — actual sum is 13. Out-of-scope this round (plan is contract, not running text). Suggest fixing in v0.2.0 plan revision OR leaving as-is since plan is now executed.
  - v0.1.0-alpha.2-meta-external-audit-verdict: /Users/archiesun/Desktop/Arc Studio/arcgentic/docs/audits/v0.1.0-alpha.2-meta-external-audit-verdict.md:61 — - D-v0.1.0-a2-meta-2 (P3): yaml_set / yaml_safe_dump does not preserve init.sh's top-of-file comment lines (`# .agentic-rounds/state.yaml — single source ...`). Cosmetic only; state.yaml is gitignored so users never see persisted comments anyway. Suggest noting in `yaml.sh` docstring for future yaml_get callers.

## Prevention Rule

Before closing a round, check whether `future fact audit state both` appears in the planned
handoff, implementation notes, self-audit, or external audit evidence.
