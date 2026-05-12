# {round_name} — Fix-Round Handoff

**Phase**: {phase_label}
**Round**: {round_name} (fix-round for prior {parent_round_name} findings)
**Type**: fix-round (narrow scope)
**Mandate level**: Mandate #17(d) FULL-STRENGTH; scope-narrowed
**Prior-round anchor**: `{prior_round_anchor}` ({parent_round_name})
**Findings being addressed**: {list of finding-IDs from parent verdict}
**Audit script**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`

---

## 1. Scope (narrow)

### 1.1 Round identity + parent verdict reference
### 1.2 Findings being addressed (1 per finding-ID)
### 1.3 Anti-scope (what NOT to fix even if tempting)

## 2. Reference scan (if any new references needed; usually empty)

{4-column triplet table; may be empty if no new references}

| Reference | Why used | What part | License + RT tier |
|---|---|---|---|
| {ref-name} | {1-sentence rationale} | {pinpoint shape: function / pattern / API} | {license: MIT/Apache/AGPL/etc} + RT{0/1/2/3} |

## 3. Toolkit scan (per mandate #14)

{Skills + agents + connectors that will be invoked for this fix}

## 4. Per-finding fix plan

### 4.1 Finding-ID-1: {fix approach}
### 4.2 Finding-ID-2: {fix approach}
### 4.N ...

(One subsection per finding being addressed.)

## 5. 4-commit chain plan

### Commit 1 — Entry-admin
### Commit 2 — BA design pass (smaller scope)
### Commit 3 — Dev body (fix only — no new features)
### Commit 4 — State refresh + audit handoff
### CI handling per mandate #25 (d)

## 6. Test plan (additive only; existing tests preserved)

{File-level table; new tests only — existing tests must not regress}

| File | Type | Tests | Coverage focus |
|---|---|---|---|
| {file-path} | unit / property / integration | {test names} | {what aspect tested} |

## 7. Mandate compliance plan

### 7.1 - 7.N (same as 18-section, possibly fewer mandates apply)

## 8. Forward-debt projections (usually 0 NEW)

{Fix-rounds typically don't add new forward-debts; should net DECREASE the count}

## 9. Quality gates per mandate #25 (a)

### 9.1 Pre-commit checklist
### 9.2 Failure escalation

## 10. Self-audit fact-shape targets (smaller; ~15-20 facts)

### 10.1 Commit chain anchors (4 facts)
### 10.2 Per-finding remediation evidence (5-10 facts)
### 10.3 No-regression facts (3-5 facts)
### 10.4 Tests pass + quality gates (5 facts)

## 11. Audit handoff target path + format

{Path: `docs/audits/phase-{P}/{round_id}.md`. Format: spec § 9 self-audit template.}

## 12. Next round preview

{Typically: returning to substrate-touching after this fix lands}

---

*Fix-round handoff written by planner agent (arcgentic v{VERSION}).*
