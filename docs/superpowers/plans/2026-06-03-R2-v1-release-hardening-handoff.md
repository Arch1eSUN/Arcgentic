# R2-v1-release-hardening — Project Mode + Closeout Handoff

**Phase**: arcgentic v1.0.0
**Round**: R2-v1-release-hardening
**Type**: substrate-touching release-hardening round
**Prior-round anchor**: `a38e6780aa4d7ba358ce869a7e0e2558c306c470`
**Inherited project session mode**: `multi-session`
**Design contract**: `docs/plans/2026-06-02-arcgentic-v1-openspec-superpowers-design.md`
**R1 verdict**: `docs/audits/R1-v1-openspec-marketplace.md`
**Cost discipline**: no paid API calls, no background polling, no automatic third-party plugin install

---

## 1. Scope

Allowed scope: turn the R1 dogfood findings into first-class V1 workflow surfaces and
prepare the project for a v1.0.0 release. This round implements project-level session
mode, orchestrator dispatch order, close-round lifecycle handling, session prompt role
selection, and release-surface hardening.

This round is both development and live dogfood. The implementation must treat real
workflow confusion observed during R1 as source evidence, not as out-of-band chat context.
The user-visible defect is: after developer work and external audit PASS, the workflow did
not clearly say who closes the round, what gets anchored, and which session starts next.

Forbidden scope: do not reimplement R1 source-intake/capability/spec modules unless needed
for compatibility. Do not touch Moirai. Do not add hosted services, paid APIs, background
processes, or automatic third-party installs. Do not tag v1.0.0 until this round passes
external audit.

## 2. Reference Scan

| Reference | Use mode | Why used | What part | License + RT tier |
|---|---|---|---|---|
| `docs/audits/R1-v1-openspec-marketplace.md` | direct use | Captures the passed R1 implementation and P2 prompt-role debt | finding `D-R1-v1-openspec-marketplace-1`, 19/19 fact table | project-owned; RT3 |
| `docs/tech-debt.md` | direct use | Records active closeout and role-selector debts | `R1-CLOSEOUT-SEAM`, `R1-SESSION-PROMPT-ROLE` | project-owned; RT3 |
| `skills/using-arcgentic/SKILL.md` | direct use | Current role model and state-machine entrypoint | four-role workflow, two operating modes | project-owned; RT3 |
| `skills/orchestrate-round/SKILL.md` | direct use | Current orchestrator behavior | sub-agent verification, `passed -> closed` note | project-owned; RT3 |
| `schema/state.schema.json` | direct use | State interface that must represent project mode and closeout anchors | `current_round`, `last_passed_round`, `audit_verdict` | project-owned; RT3 |
| `msitarzewski/agency-agents` / `jnMetaCode/agency-agents-zh` | reference-only | Role handoff language and role-family routing | identity/mission/deliverable shape; no role body import | MIT + RT0 |

No external source code may be copied into runtime.

## 3. Tooling Plan

Expected skills: `arcgentic:using-arcgentic`, `arcgentic:plan-round`,
`arcgentic:execute-round`, `arcgentic:audit-round`, and future `arcgentic:close-round`.

Expected commands:

- `bash scripts/state/pickup.sh --state-file .agentic-rounds/state.yaml`
- `bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml`
- `python3 -m arcgentic.cli audit-check <verdict> --strict-extended`
- `python3 -m arcgentic.cli v1-release-readiness --repo-root .`
- `cd toolkit && pytest --tb=short -q`
- `cd toolkit && mypy --strict src/ tests/`
- `cd toolkit && ruff check .`
- `python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic`

Project mode is already decided: `multi-session`. Rounds must inherit it and must not ask
for mode again unless the founder explicitly changes project topology.

## 4. Architecture Target

Add or refine these seams:

- `project-session-mode`: project-level topology decision, stored once and inherited by
  rounds.
- `orchestrator-dispatch`: plan-generated order of which session starts next, what prompt
  to paste, and what stop condition returns control.
- `close-round`: closes a passed round by verifying/anchoring the audit verdict, scanning
  lessons/debt, transitioning `passed -> closed`, and emitting next-round recommendation.
- `session-mode prompt --role developer|auditor|closeout`: role-specific prompt selection
  for inherited multi-session mode.
- `v1-release-readiness`: final version/docs/manifest/install/tag-readiness checks.

The deep seam is the orchestrator lifecycle: planning, dispatch, verification, closeout,
and next-round handoff should live behind a small CLI/skill interface.

## 5. Implementation Tasks

Implementation task 1: move session-mode from round-level questioning to project-level
topology. Add state/config support and docs that say rounds inherit the chosen mode.

Implementation task 2: add orchestrator dispatch output. A completed handoff must say which
session starts first, which identity prompt to paste, the stop condition, and what the
orchestrator does after that session returns.

Implementation task 3: implement a first-class `close-round` CLI/skill seam. It must handle
audit verdict presence, strict audit-check, audit commit anchor, lesson/debt scan, state
transition, and next-round handoff recommendation.

Implementation task 4: add `session-mode prompt --role developer|auditor|closeout` and keep
existing `--mode multi-session` behavior backward compatible.

Implementation task 5: harden external audit verdict requirements so `PASS`,
`NEEDS_FIX`, and `AUDIT_INCOMPLETE` are structured outcomes. Any finding must include
priority, location/evidence, expected, actual, recommended fix, and verification.

Implementation task 6: update `using-arcgentic`, `orchestrate-round`, `plan-round`,
`audit-round`, README, README.zh-CN, manifests, and release docs to reflect the project
mode + orchestrator dispatch + closeout loop.

Implementation task 7: run V1 release readiness checks but do not create the v1.0.0 tag
inside the developer session. Tagging is a founder/orchestrator release action after audit.

## 6. Required Tests

Required test: project-level session mode is stored/read once and inherited by new rounds.

Required test: starting a second round does not ask for session mode again when project mode
is set.

Required test: handoff generation includes a dispatch order with next session, identity
prompt, stop condition, and return signal.

Required test: `session-mode prompt --role developer` and `--role auditor` return distinct
prompts for the same round.

Required test: close-round refuses to run before state is `passed`.

Required test: close-round refuses a PASS verdict with missing or unanchored audit commit.

Required test: close-round updates state to `closed` and records `last_passed_round`.

Required test: verdict completeness rejects bare `NEEDS_FIX` without structured findings.

Required test: V1 release readiness passes after docs/manifests/version surfaces are aligned.

## 7. Required Audit Facts

Required audit fact 1: `.agentic-rounds/state.yaml` validates against
`schema/state.schema.json` after closeout fields are written.

Required audit fact 2: project session mode is not requested per round; R2 inherits
`multi-session`.

Required audit fact 3: R2 handoff includes dispatch order and identity prompts.

Required audit fact 4: close-round refuses invalid states and unanchored verdicts in tests.

Required audit fact 5: close-round closes a synthetic passed round in tests.

Required audit fact 6: role-specific session prompts are distinct and selectable.

Required audit fact 7: audit verdict completeness checks distinguish PASS, NEEDS_FIX, and
AUDIT_INCOMPLETE.

Required audit fact 8: `python3 -m arcgentic.cli v1-release-readiness --repo-root .` reports
`ok: true` or a precise blocker list.

Required audit fact 9: plugin validator passes for `/Users/archiesun/plugins/arcgentic`.

Required audit fact 10: anti-scope grep proves no Moirai path was modified.

## 8. Stop Conditions

Stop if project-level session mode storage would require rewriting closed R1 history. Add a
forward-compatible config/state field instead.

Stop if close-round needs to commit files automatically without explicit founder/orchestrator
control. The first V1 version may emit commands rather than perform destructive git actions.

Stop if any release action would tag or publish without external audit PASS.

Stop if state schema changes make existing R1 state invalid.

Stop if the developer session is tempted to write the external audit verdict.

## 9. BA Design Brief

BA designer should decide where project-level session mode lives: `.agentic-rounds/state.yaml`,
a project config file, or a generated handoff field. The decision must preserve local-first
behavior and avoid asking the same mode question every round.

BA should also define closeout ownership. The expected product model is: orchestrator owns
closeout; developer owns implementation and self-audit; auditor owns external verdict.

## 10. CR Review Brief

CR reviewer should prioritize lifecycle coherence over feature count. Look for shallow CLI
commands that only print text, state/schema drift, role contamination, and mismatch between
human-readable prompts and machine-verifiable gates.

CR must challenge any implementation where close-round silently mutates Git history or hides
required founder confirmation.

## 11. SE Contract Brief

SE receives only sections 1-8 and public interface contracts. Do not pass BA design rationale.

Threat surfaces: path traversal in verdict/handoff paths, accidental commit of untracked
local files, role prompt leakage across sessions, state mutation from the wrong state,
malformed verdict findings, and release commands that publish/tag before audit.

## 12. Commit Plan

Commit 1: R2 handoff and state planning update.

Commit 2: project-level session mode model, schema/config update, and tests.

Commit 3: orchestrator dispatch and role-specific session prompt support.

Commit 4: close-round CLI/skill seam and closeout tests.

Commit 5: audit verdict completeness checks and docs/skill updates.

Commit 6: release readiness docs/manifests alignment and self-audit handoff.

The developer may split further if a commit would become too broad, but every commit must
have a clear verification surface.

## 13. Quality Gates

Every code commit must run:

- `cd toolkit && pytest --tb=short -q`
- `cd toolkit && mypy --strict src/ tests/`
- `cd toolkit && ruff check .`
- `bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml`
- `python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic`

Every audit or closeout artifact must additionally run:

- `python3 -m arcgentic.cli audit-check <verdict> --strict-extended`
- `bash scripts/gates/verdict-fact-table-gate.sh --state-file .agentic-rounds/state.yaml`

## 14. State Handling

State file: `.agentic-rounds/state.yaml`.

Current round id: `R2-v1-release-hardening`.

Inherited project session mode: `multi-session`.

Expected state path: `planning -> awaiting_dev_start -> dev_in_progress -> awaiting_audit
-> audit_in_progress -> passed -> closed`.

The orchestrator controls state transitions. Developer session may update dev/self-audit
fields and transition to `awaiting_audit` only after implementation is committed and gates
are green.

## 15. Dispatch Order

Step 1: Orchestrator writes and validates this handoff, then stops before development.

Step 2: Founder starts Developer Session using section 16. Developer does implementation,
self-audit, and transition to `awaiting_audit`.

Step 3: Orchestrator verifies state, commit chain, and self-audit. If valid, founder starts
Auditor Session using section 17.

Step 4: Auditor writes external verdict and transitions to `passed` or `needs_fix`.

Step 5: If PASS, orchestrator runs closeout. R2 should dogfood the new `close-round` seam.
If NEEDS_FIX, orchestrator dispatches a fix Developer Session with only the structured
findings as scope.

## 16. Devsession Message

You are the Developer Session for arcgentic round `R2-v1-release-hardening`.

Read: `AGENTS.md`, `.agentic-rounds/state.yaml`, this handoff, `docs/tech-debt.md`, and
`docs/audits/R1-v1-openspec-marketplace.md`.

Start round: `R2-v1-release-hardening` developer implementation.

Stop after: implementation commits and self-audit handoff are complete, all quality gates
pass, `current_round.dev_commits` and `current_round.self_audit_doc` are recorded, and
state is transitioned to `awaiting_audit`.

Detailed read order:

1. `AGENTS.md`
2. `.agentic-rounds/state.yaml`
3. `docs/superpowers/plans/2026-06-03-R2-v1-release-hardening-handoff.md`
4. `docs/tech-debt.md`
5. `docs/audits/R1-v1-openspec-marketplace.md`

Identity boundary: developer only. Do not write external audit verdict. Do not close the
round unless the new close-round seam is being tested against a synthetic fixture; real
R2 closeout belongs to orchestrator after external audit PASS.

Start condition: state is `awaiting_dev_start` and orchestrator has handed this prompt to
the founder.

Recommended agency role family: software architect plus workflow engineer plus test
engineer. Do not adopt auditor identity.

## 17. Auditor Session Handoff

You are the External Auditor Session for arcgentic round `R2-v1-release-hardening`.

Start only when `.agentic-rounds/state.yaml` is `awaiting_audit` or `audit_in_progress`.

Read in order:

1. `AGENTS.md`
2. `.agentic-rounds/state.yaml`
3. This handoff
4. Developer self-audit handoff
5. Every commit in `current_round.dev_commits`

Identity boundary: auditor only. Do not implement fixes. Do not plan R3. Re-run mechanical
facts independently. If state is wrong, return `AUDIT_INCOMPLETE / STATE MISMATCH`.

Verdict requirements: every P0/P1/P2/P3 finding must include priority, evidence location,
expected, actual, recommended fix, and verification. A bare `PASS` or `NEEDS_FIX` is invalid.

## 18. Closeout and Next Round

After external audit PASS, orchestrator owns closeout.

Closeout must:

1. Verify verdict file exists.
2. Run strict audit-check.
3. Anchor audit commit.
4. Run lesson/debt scan.
5. Transition `passed -> closed`.
6. Emit the next-round recommendation.

Expected next step after R2 PASS: final founder-controlled V1.0.0 release action, including
tag creation and push only after all R2 facts are anchored.

This handoff is written from live arcgentic-on-arcgentic dogfood. The R2 product target is
to remove the exact confusion observed after R1: mode is project-level, orchestrator directs
sessions, and PASS has a deterministic closeout path.
