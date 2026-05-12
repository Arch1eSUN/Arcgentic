# {round_name} — Entry-Admin + Dev Handoff

**Phase**: {phase_label}
**Round**: {round_name} ({round_id})
**Type**: substrate-touching round
**Mandate level**: Mandate #17(d) FULL-STRENGTH; clause (h) Option A {Nth} round
**Prior-round anchor**: `{prior_round_anchor}` ({prior_round_name})
**Audited HEAD**: forward-deferred to dev-body commit per § 8.11 (a) + (f)
**Audit script**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`
**CI status**: {available | UNAVAILABLE — local-substitute MANDATORY}

---

## 1. Scope

### 1.1 Round identity + prior anchor

{1-2 paragraphs identifying this round and citing the prior 40-char anchor}

### 1.2 Vision anchor — N user-facing examples

{N=3-5 user-facing examples illustrating what this round enables}

### 1.3 Dev body deliverables

{File-level list of what dev body commit 3 produces}

### 1.4 Architecture overview — N-layer separation

{Architecture diagram or N-layer summary}

### 1.5 Anti-scope (NOT delivered this round)

{Explicit list of what this round does NOT do; mechanically verifiable via grep}

### 1.6 Cost-discipline preserved

{Confirm: no paid-API calls; no background daemons; Claude Code subscription only}

### 1.7 Why this round matters

{1 paragraph strategic motivation}

### 1.8 Inherited forward-debt dispositions from prior round

{Per debt-ID from prior round's audit handoff: status — addressed / forward-carried / re-scoped}

## 2. Reference scan (mandate § 8.12 (a) + (e) + RT vocab #13 (h))

{4-column triplet table:}

| Reference | Why used | What part | License + RT tier |
|---|---|---|---|
| {ref-name} | {1-sentence rationale} | {pinpoint shape: function / pattern / API} | {license: MIT/Apache/AGPL/etc} + RT{0/1/2/3} |

(Minimum 1 row; ideally 3-5 rows for substrate rounds.)

## 3. Toolkit + skill scan (mandate #14)

### 3.1 Skills expected to be invoked
### 3.2 Skills explicitly NOT invoked
### 3.3 MCP / plugin / connector scan
### 3.4 Agency-agents scan
### 3.5 References INDEX scan

## 4. BA design pass brief (dispatch ba-designer agent)

{Self-contained brief that will be passed to the ba-designer agent. Spec § 5.3 contract.
Must include:
- Round name + scope (from § 1)
- Architectural target (1 sentence)
- Reference subset available (from § 2)
- Required output sections (per spec § 8 BA design template)
- Quality bar (no TBD/TODO; D-1..D-N decisions with rationale + alternatives rejected)}

## 5. 4-commit chain plan

### Commit 1 — Entry-admin

{Files modified: handoff + CLAUDE.md § state row + vault current-state.md sync. No code.}
**Commit subject**: `docs({round}): entry-admin handoff — {feature} ({position})`

### Commit 2 — BA design pass

{Files modified: docs/design/{ROUND_UPPER}_BA_DESIGN.md. No code.}
**Commit subject**: `docs({round}/design): BA design pass — {core decisions}`

### Commit 3 — Dev body

{Files modified: list source + test files. The ONLY code commit.}
**Commit subject**: `feat({round}): {round_id} dev body — {summary}`
**Local 4-gate quality check**: mypy --strict + pytest + ruff + audit-check dry-run

### Commit 4 — State refresh + audit handoff

{Files modified: docs/audits/phase-{P}/{round}.md + CLAUDE.md + vault. No code.}
**Commit subject**: `docs(audit/{round}): {round_id} self-audit handoff + state refresh`

### CI handling per mandate #25 (d)

{If CI unavailable: local 4-gate is canonical; document expected gates}

## 6. Test plan (file-level coverage)

| File | Type | Tests | Coverage focus |
|---|---|---|---|
| {file-path} | unit / property / integration | {test names} | {what aspect tested} |

## 7. Mandate compliance plan

### 7.1 Mandate #25 (a)+(b) elevated rigor
### 7.2 Mandate #24 EXTENSION
### 7.3 Mandate #21 license-not-constraint
### 7.4 Mandate #17(d) clause (h) Option A
### 7.5 Mandate #20 SE CONTRACT-ONLY briefing
### 7.6 Mandate #13 clause (h) RT vocabulary
### 7.7 Lesson 8 STRUCTURAL-LAW streak preservation

## 8. ★ Round-specific feature codification 1 (if applicable)

{Substrate-specific: how the new module/Protocol/event preserves Lesson 8 streak}

## 9. ★ Round-specific feature codification 2 (if applicable)

{Same shape for a second codified feature, if round delivers multiple}

## 10. Forward-debt projections

### 10.1 Inherited from prior round
### 10.2 NEW projected forward-debts

{Per-debt: ID | severity P{0/1/2/3} | description | owner-round}

## 11. Quality gates per mandate #25 (a) — MANDATORY at every commit

### 11.1 Pre-commit checklist
### 11.2 Failure escalation

## 12. Self-audit fact-shape targets

### 12.1 Commit chain anchors (4 facts)
### 12.2 Substantive code presence (10-12 facts)
### 12.3 Round-specific surface (5-6 facts)
### 12.4 EventLog events (3-5 facts)
### 12.5 Anti-scope grep facts (4-6 facts)
### 12.6 Tests pass + quality gates (5 facts)
### 12.7 Mandate compliance + state row (5-8 facts)

(Total expected: 25-40 facts spread across subsections.)

## 13. Audit handoff target path + format

{Path: `docs/audits/phase-{P}/{round_id}.md`. Format: per spec § 9 self-audit handoff template.}

## 14. Security threat surfaces — SE CONTRACT-ONLY brief (mandate #20)

### 14.1 {threat surface 1}
### 14.2 {threat surface 2}
### 14.3 {threat surface 3}
### 14.4 {threat surface 4}
### 14.5 {threat surface 5}

(5-6 threat surfaces. SE agent receives THIS brief + contract text only — NOT BA design.)

## 15. Why this round matters — strategic summary

{1-2 paragraph closing strategic motivation}

## 16. Next round preview

{What round(s) come after this one + their dependencies on this round's deliverables}

## 17. Open issues / decisions deferred to BA design pass

{Items the BA designer will resolve during commit 2}

## 18. Acknowledgments

{Authoring agent (planner agent), arcgentic version, date}

---

*Substrate-touching round handoff written by planner agent (arcgentic v{VERSION}).*
