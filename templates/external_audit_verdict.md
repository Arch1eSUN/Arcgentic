# {round_name} — External Audit Verdict

**Phase**: {phase_label}
**Round**: {round_name}
**Type**: substrate-touching / fix-round / admin
**External auditor**: {auditor identity — different from execute-round agent that wrote self-audit}
**Date**: {YYYY-MM-DD}
**Audit script (re-run)**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`

---

## § 1. Executive summary

{2-3 sentences: round identity + outcome + headline finding}

**Verdict**: PASS / NEEDS_FIX

**One-line summary**: {single sentence capturing what's worth knowing}

## § 2. Findings

### 2.1 P0 (blocking — must fix before close)

{If any. List per-finding with: file:line, evidence, recommendation.}

| ID | File:line | Evidence | Recommendation |
|---|---|---|---|
| P0-1 | {file:line} | {evidence} | {recommendation} |

### 2.2 P1 (important — fix before next substrate round)

| ID | File:line | Evidence | Recommendation |
|---|---|---|---|
| P1-1 | {file:line} | {evidence} | {recommendation} |

### 2.3 P2 (non-blocking — should become forward-debt)

| ID | File:line | Evidence | Recommendation |
|---|---|---|---|
| P2-1 | {file:line} | {evidence} | {recommendation} |

### 2.4 P3 (informational — note for retrospective)

| ID | Observation | Notes |
|---|---|---|
| P3-1 | {observation} | {notes} |

(External auditor finds 2-5 P0/P1/P2 findings typically; 5-10 P3 observations.)

## § 3. Special audit attention assessment

{For substrate-touching rounds, the auditor calls out any patterns that deserve elevated future attention:}

- {Pattern A}: assessment {strong / nominal / weak}
- {Pattern B}: assessment {strong / nominal / weak}

## § 4. Mandate compliance

| Mandate | Applied? | Implementation quality | Notes |
|---|---|---|---|
| #17(d) clause (h) | YES | strong / nominal / weak | {evidence} |
| #20 SE CONTRACT-ONLY | YES | strong / nominal / weak | {evidence} |
| #24 EXTENSION | YES if substrate-touching | strong / nominal / weak | {evidence} |
| #25 (a) elevated rigor | YES | strong / nominal / weak | {evidence} |

## § 5. Lesson 8 STRUCTURAL-LAW codification result

**Streak**: {N}-of-{N} (prior streak: {N-1}-of-{N-1}) — {PRESERVED / RESET}

**Preservation type**: {type cited from handoff § 7.7 — confirmed observed / declined to preserve / declared NOVEL}

## § 6. Cumulative forward-debt count (external audit confirmation)

| Self-audit reported | Auditor verified | Discrepancy |
|---|---|---|
| {N} | {N} | {none / explain} |

## § 7. Anti-formalism check

{Auditor's check that the round's documentation isn't merely "going through motions" — concrete evidence that decisions weren't rubber-stamped:}

- {Check A: ...}: {result}
- {Check B: ...}: {result}

## § 8. Cross-cutting items (if any)

{Anything the auditor flags that doesn't fit § 1-7. Examples: cost-discipline anomaly, anti-contamination concern, ecosystem-wide pattern.}

- {Item A}: {description}

## § 9. Mechanical audit facts (independent re-run)

{Auditor's own audit-check facts table — separate from self-audit's § 7. May overlap with self-audit's facts but auditor verifies independently.}

| # | Command | Expected | Auditor's actual | Match? |
|---|---|---|---|---|
| 1 | {cmd} | {expected} | {actual} | Y/N |
| 2 | {cmd} | {expected} | {actual} | Y/N |
| ... | ... | ... | ... | ... |

## § 10. Verdict line

**FINAL VERDICT**: PASS / NEEDS_FIX

(Single line; copied to round's audit-trail summary.)

### Sign-off

External auditor identity: {auditor-name + version}
Audit date: {YYYY-MM-DD}
Audit duration: {hours}

---

*External audit verdict for {round_name} written by external auditor (independent from self-audit agent).*
