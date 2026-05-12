# {round_name} — Self-Audit Handoff

**Phase**: {phase_label}
**Round**: {round_name}
**Type**: substrate-touching / fix-round / admin
**Authoring agent**: execute-round skill (arcgentic v{VERSION}) at commit 4 of 4-commit chain
**Date**: {YYYY-MM-DD}
**Audit script**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`

---

## § 1. Scope

### 1.1 Summary

{1 paragraph: what this round delivered, citing 4-commit chain anchors and BA design D-decisions}

### 1.2 Mandate posture

{Mandates that applied + their state: PRESERVED / EXTENDED / amended}

## § 2. Decisions Verified (BA + CR + SE three-way reconciliation per mandate #17(d) clause (h) Option A)

### 2.1 BA design pass summary

{Output from ba-designer agent dispatch in Phase 2 of execute-round 4-commit chain.
Includes: D-1..D-N decisions list + reference scan summary + file-decomp file count
+ test plan test count.}

| D-ID | Decision (1-line) | Implemented in (file:line) | Notes |
|---|---|---|---|
| D-1 | {decision} | {file:line} | {status: implemented / partial / deferred (with debt ID)} |

### 2.2 CR inline pass (per cr-reviewer dispatch)

{P0/P1/P2/P3 findings from cr-reviewer agent dispatch in Phase 3:}

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| CR-1 | P{0/1/2/3} | {finding with file:line} | {Inline-closed: see commit XYZ / Forward-debt: {DEBT-NAME} / Disagreed: {reason}} |

(Expected count: 3-7 findings.)

### 2.3 SE CONTRACT-ONLY pass (per se-contract dispatch — mandate #20 LOAD-BEARING)

{NOVEL P3 findings from se-contract agent. Reminder: SE did NOT see the BA design doc.}

| ID | Sev | Threat surface | Finding | Disposition |
|---|---|---|---|---|
| SE-1 | P{2/3} | {category} | {finding} | {Forward-debt {DEBT-NAME} / Inline-closed} |

(Expected count: 3-6 NOVEL P3 findings.)

## § 3. Toolkit + skill scan (mandate #14)

{What skills + agents + connectors were invoked during this round:}

| Skill / agent / connector | Invocation count | Cost | Notes |
|---|---|---|---|
| {name} | {N} | {token usage / subprocess count} | {what it produced} |

## § 4. Commits + CI evidence

{4-commit chain SHAs + git log evidence:}

| Position | SHA (40-char) | Subject |
|---|---|---|
| Commit 1 (entry-admin) | {SHA40} | {subject} |
| Commit 2 (BA design) | {SHA40} | {subject} |
| Commit 3 (dev body) | {SHA40} | {subject} |
| Commit 4 (state+audit) | {SHA40} | {subject — this commit} |

CI status: {available — link to job / UNAVAILABLE — local 4-gate is canonical per mandate #25 (d)}

## § 5. Quality gates

{Per-gate result table:}

| Gate | Status | Output |
|---|---|---|
| mypy --strict {dirs} | PASS / FAIL | "Success: no issues found in N source files" |
| pytest --tb=no | PASS / FAIL | "N passed" |
| ruff check . | PASS / FAIL | "All checks passed!" |
| arcgentic audit-check ... --strict-extended | PASS / FAIL | "N/N PASS + AC-1 + AC-3 PASS" |

## § 6. Forward-debts (this round's delta)

### 6.1 Inherited from prior round

{Per-debt: ID | Severity | Description | Status after this round (addressed / forward-carried)}

| Debt ID | Severity | Description | Status |
|---|---|---|---|
| {DEBT-NAME} | P{1/2/3} | {description} | {addressed / forward-carried} |

### 6.2 NEW from this round

{Per-debt: ID | Severity | Description | Owner-round (next round that addresses it)}

| Debt ID | Severity | Description | Owner-round |
|---|---|---|---|
| {DEBT-NAME} | P{1/2/3} | {description} | {next round} |

### 6.3 Aggregate count

| Prior count | Newly added | Resolved | Net change | Post-round count |
|---|---|---|---|---|
| {N} | +{N_new} | -{N_resolved} | {delta} | {N_post} |

## § 7. Mechanical audit facts

{Markdown 4-column fact table; per spec § 14 audit-check engine format:}

| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | `cd <repo> && git log --oneline {commit_4_sha} -n 4 \| wc -l` | `4` | 4-commit chain present |
| 2 | `cd <repo> && grep -cE 'def\s+run\(' toolkit/src/arcgentic/skills_impl/plan_round.py` | `1` | plan_round.run exists |
| 3 | {command} | {expected} | {comment} |
| ... | ... | ... | ... |

(Target: 25-40 facts split across handoff subsections. AC-1 + AC-3 checks via --strict-extended.)

## § 8. Verdict

{Final verdict line:}

**STATUS: PASS** (all gates clean; CR found {N} P0/P1; SE found {N} NOVEL P3; all addressed/registered as forward-debt)

OR

**STATUS: NEEDS_FIX** — see § 8.1 fix plan

### 8.1 Fix plan (if NEEDS_FIX)

{What the next fix-round must address: per-finding plan with priority and target round}

| Finding ID | Source | Priority | Target round | Fix description |
|---|---|---|---|---|
| {CR-N / SE-N} | {cr-reviewer / se-contract} | P{0/1} | {round_name} | {what to fix} |

---

*Self-audit handoff for {round_name} written by execute-round skill (arcgentic v{VERSION}).*
