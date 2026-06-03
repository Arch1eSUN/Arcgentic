# R3-v1-prepublish-fix — Stable Audit Facts + Lesson Precision Handoff

**Phase**: arcgentic v1.0.0 pre-publish fix
**Round**: R3-v1-prepublish-fix
**Type**: fix-round / release-hardening
**Prior-round anchor**: `ab7018204c2df6578a7f8f3abec7c43165f12d21`
**Inherited project session mode**: `multi-session`
**Trigger**: founder decision to fix R2 P2 dogfood findings before V1 release
**Cost discipline**: no paid API calls, no background polling, no automatic third-party plugin install

---

## 1. Scope

Allowed scope: fix the two R2 dogfood P2 findings that the founder decided must land before
V1 release:

1. Developer self-audit fact generation must avoid mutable current state and moving `HEAD`.
2. `codify-lesson` / closeout lesson scan must stop producing noisy lesson/amendment
   clusters from broad verdict prose.

Forbidden scope: do not reopen R2 architecture work, do not add new source-intake or
close-round capabilities beyond what is required to fix these two findings, do not tag or
publish v1.0.0, do not touch Moirai, and do not absorb v0.3 debts such as execute-round
retry loops or richer commit-chain fact generation.

This round is the final prepublish cleanup before the V1 release cut. It should be small,
test-heavy, and bounded.

## 2. Reference Scan

| Reference | Use mode | Why used | What part | License + RT tier |
|---|---|---|---|---|
| `docs/audits/R2-v1-release-hardening.md` | direct use | Source verdict for the two prepublish issues | finding `D-R2-v1-release-hardening-1`, fact rows 3-4, forward debt | project-owned; RT3 |
| `docs/audits/R2-v1-release-hardening-self-audit.md` | direct use | Shows mutable `current state` and `HEAD` facts that became stale | fact rows #3 and #19 | project-owned; RT3 |
| `docs/tech-debt.md` | direct use | Tracks release-blocking prepublish debts | `R2-SELF-AUDIT-MUTABLE-FACTS`, `R2-CODIFY-LESSON-PRECISION` | project-owned; RT3 |
| `toolkit/src/arcgentic/skills_impl/execute_round.py` | direct use | Likely self-audit fact generation seam | self-audit handoff writing and fact table generation | project-owned; RT3 |
| `toolkit/src/arcgentic/skills_impl/codify_lesson.py` | direct use | Lesson clustering implementation seam | finding extraction / pattern promotion | project-owned; RT3 |
| `toolkit/src/arcgentic/utils/pattern_detection.py` | direct use | Pattern detection support seam | clustering token/slug logic | project-owned; RT3 |

No external source is needed for this round.

## 3. Tooling Plan

Project session mode remains `multi-session`; do not ask again.

Expected commands:

- `bash scripts/state/pickup.sh --state-file .agentic-rounds/state.yaml`
- `bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml`
- `cd toolkit && pytest --tb=short -q`
- `cd toolkit && mypy --strict src/ tests/`
- `cd toolkit && ruff check .`
- `python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic`
- `python3 -m arcgentic.cli v1-release-readiness --repo-root .`

The developer should add focused tests first, then implementation. Do not rely only on
manual inspection of generated markdown.

## 4. Architecture Target

Two seams should become deeper and more stable:

- `execute-round self-audit facts`: generated fact rows should check immutable artifacts,
  fixed commit anchors, or state history. They must not depend on current mutable state or
  moving `HEAD` after the external auditor/closeout commits.
- `codify-lesson pattern extraction`: lesson promotion should use structured finding rows
  and stable summary/evidence fields, not broad prose from reference tables, author notes,
  or unrelated forward-debt rows.

The target is not a new abstraction layer. The target is tighter, more deterministic
interfaces at existing seams.

## 5. Implementation Tasks

Implementation task 1: add regression tests proving developer self-audit facts remain
valid after state advances from `awaiting_audit` to `audit_in_progress` and after `HEAD`
moves past the dev self-audit commit.

Implementation task 2: update self-audit generation so it uses state history or fixed
anchors. The expected replacement shape is:

- validate that `awaiting_audit` appears in `current_round.state_history`;
- validate `current_round.self_audit_doc.commit` resolves via `git cat-file`;
- validate the self-audit doc path exists at that fixed commit;
- avoid `git rev-parse HEAD == self_audit_doc.commit`.

Implementation task 3: add regression tests for codify-lesson precision using R2-style
audit content. The test should fail if the generated slug resembles
`future-fact-audit-state-both` or if unrelated reference/debt prose is counted as examples.

Implementation task 4: update `codify-lesson` / pattern detection to cluster from structured
findings first. Prefer finding id, priority, summary, and evidence. Exclude reference scan,
author note, and general forward-debt prose unless they are inside a findings table row.

Implementation task 5: update docs/skills only where necessary so future developer/auditor
sessions know self-audit facts must be stable across audit and closeout transitions.

Implementation task 6: update `docs/tech-debt.md` by moving the two R2 prepublish debts to
Resolved when tests and implementation prove the fixes.

## 6. Required Tests

Required test: generated self-audit fact table contains no current-state assertion like
`current_round.state == awaiting_audit`.

Required test: generated self-audit fact table contains no moving-HEAD equality check like
`git rev-parse HEAD == self_audit_doc.commit`.

Required test: self-audit fact table still passes after a synthetic state advances to
`audit_in_progress`.

Required test: self-audit fact table still passes after `HEAD` advances beyond the dev
self-audit commit, using fixed commit anchors instead.

Required test: codify-lesson extracts examples only from structured findings rows.

Required test: R2-style verdict text does not generate a noisy slug like
`future-fact-audit-state-both`.

Required test: codify-lesson still promotes a real repeated structured finding pattern.

Required test: full toolkit pytest, mypy strict, ruff, plugin validator, and
v1-release-readiness all pass.

## 7. Required Audit Facts

Required audit fact 1: R3 dev commit chain resolves and matches state.

Required audit fact 2: `docs/audits/R3-v1-prepublish-fix-self-audit.md` strict audit-check
passes after the auditor has moved state forward.

Required audit fact 3: grep proves the new self-audit generated facts do not assert current
state equals `awaiting_audit`.

Required audit fact 4: grep proves the new self-audit generated facts do not compare moving
`HEAD` to `self_audit_doc.commit`.

Required audit fact 5: tests cover a synthetic post-dev `HEAD` advance.

Required audit fact 6: tests cover a synthetic `awaiting_audit -> audit_in_progress`
transition.

Required audit fact 7: codify-lesson no longer emits `future-fact-audit-state-both` for the
R2-style fixture.

Required audit fact 8: codify-lesson still emits a stable, meaningful lesson for a repeated
structured finding fixture.

Required audit fact 9: `docs/tech-debt.md` marks `R2-SELF-AUDIT-MUTABLE-FACTS` and
`R2-CODIFY-LESSON-PRECISION` resolved.

Required audit fact 10: anti-scope grep proves no Moirai path was modified and no `v1.0.0`
tag was created.

## 8. Stop Conditions

Stop if fixing codify-lesson requires a broad rewrite of the whole lesson system. In that
case, implement only a narrow structured-findings extractor and record deeper redesign as
post-release debt.

Stop if self-audit generation cannot be made stable without changing state schema. Surface
the schema change before applying it.

Stop if any test depends on wall-clock timing, current branch name, or network.

Stop if release tagging becomes tempting. This round ends before publish.

## 9. BA Design Brief

BA should preserve a clear user promise: once a developer session stops, its self-audit
handoff remains mechanically useful for auditor and closeout even after state and `HEAD`
advance.

BA should also define the lesson quality bar: a lesson title/slug must summarize a real
repeated finding pattern, not a bag of common words from unrelated markdown sections.

## 10. CR Review Brief

CR reviewer should focus on hidden parser fragility. Watch for regexes that accidentally
scan the whole verdict, parse table pipes incorrectly, or treat any repeated word as a
lesson pattern.

CR should challenge any implementation that merely special-cases the exact bad slug without
fixing the structured extraction seam.

## 11. SE Contract Brief

SE receives sections 1-8 and public interface contracts only. Do not pass BA rationale.

Threat surfaces: path traversal in audit file paths, command injection from markdown fact
tables, accidental inclusion of untracked local files, and lesson scan reading unrelated
large files outside the audit directory.

## 12. Commit Plan

Commit 1: this R3 handoff and state planning update.

Commit 2: self-audit fact stability tests and implementation.

Commit 3: codify-lesson precision tests and implementation.

Commit 4: docs/skill/tech-debt updates and developer self-audit handoff.

The developer may split further if needed, but must keep commits traceable to the two
release-blocking P2 debts.

## 13. Quality Gates

Every code commit must run:

- `cd toolkit && pytest --tb=short -q`
- `cd toolkit && mypy --strict src/ tests/`
- `cd toolkit && ruff check .`
- `bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml`
- `python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic`

Every audit artifact must additionally run:

- `python3 -m arcgentic.cli audit-check <verdict> --strict-extended`
- `python3 -m arcgentic.cli verdict-completeness <verdict>`

## 14. State Handling

State file: `.agentic-rounds/state.yaml`.

Current round id: `R3-v1-prepublish-fix`.

Inherited project session mode: `multi-session`.

Expected path: `planning -> awaiting_dev_start -> dev_in_progress -> awaiting_audit ->
audit_in_progress -> passed -> closed`.

Developer session may transition to `awaiting_audit` only after implementation, self-audit,
and local gates are complete.

## 15. Dispatch Order

Step 1: Orchestrator writes and validates this handoff, then stops before development.

Step 2: Founder starts Developer Session using section 16. Developer fixes the two scoped P2
debts, writes self-audit, and transitions to `awaiting_audit`.

Step 3: Orchestrator verifies developer return, then starts Auditor Session.

Step 4: Auditor writes external verdict and transitions to `passed` or `needs_fix`.

Step 5: If PASS, orchestrator runs closeout. If NEEDS_FIX, orchestrator dispatches a scoped
fix session using only structured findings.

## 16. Devsession Message

You are the Developer Session for arcgentic round `R3-v1-prepublish-fix`.

Read: `AGENTS.md`, `.agentic-rounds/state.yaml`, this handoff, `docs/audits/R2-v1-release-hardening.md`,
`docs/audits/R2-v1-release-hardening-self-audit.md`, and `docs/tech-debt.md`.

Start round: `R3-v1-prepublish-fix` developer implementation.

Stop after: the two R2 prepublish P2 debts are fixed, tests and quality gates pass,
developer self-audit handoff is written, `current_round.dev_commits` and
`current_round.self_audit_doc` are recorded, and state is transitioned to `awaiting_audit`.

Identity boundary: developer only. Do not write external audit verdict. Do not tag or
publish v1.0.0. Do not broaden into v0.3 debts.

Recommended agency role family: test engineer plus workflow engineer. Do not adopt auditor
or release-manager identity.

## 17. Auditor Session Handoff

You are the External Auditor Session for arcgentic round `R3-v1-prepublish-fix`.

Start only when `.agentic-rounds/state.yaml` is `awaiting_audit` or `audit_in_progress`.

Read: `AGENTS.md`, `.agentic-rounds/state.yaml`, this handoff, developer self-audit handoff,
and every commit in `current_round.dev_commits`.

Audit target: prove the two R2 P2 debts are fixed and no release/tag action occurred.

Verdict requirements: every finding must include priority, evidence, expected, actual,
recommended fix, and verification. A bare PASS/NEEDS_FIX is invalid.

## 18. Closeout and Release Gate

After external audit PASS, orchestrator owns closeout.

Closeout must run `close-round`, anchor the verdict, and verify state is `closed`.

Only after R3 is closed should the founder decide whether to cut the V1 release. Expected
next action after R3 PASS is a release cut round or founder-controlled tag action, not more
feature work.
