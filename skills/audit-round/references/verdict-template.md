# Verdict file template

Copy this verbatim to `<project>/<audits_dir>/<round-id>-external-audit-verdict.md`. Replace placeholders in `<angle-brackets>`. Every section below is REQUIRED — the `verdict-fact-table-gate.sh` won't pass if any required section is missing or empty.

---

```markdown
# `<round-id>` — External Audit Verdict

**Outcome:** PASS | NEEDS_FIX
**Audited dev commits:** `<sha40>` … `<sha40>` (chain of <N> commits)
**Audited audit commit:** (this verdict's own commit, hardcoded after writing per Rule 2 immutable-anchor — leave as `TBD` in the working draft, fill after commit)
**Auditor:** `<Claude Opus 4.X / external auditor name>`
**Audited at:** `<YYYY-MM-DD>`

## 1. Executive summary

One sentence stating PASS or NEEDS_FIX + the key reason. Examples:

> "PASS. All 15 facts verify; no P0/P1 findings; lesson codification streak advances to N-of-N with novel `<type>` preservation."

> "NEEDS_FIX. <N> P1 findings, all R1.3.1-shape (fix the example, miss the contract); fix-round must address the full input domain of the affected Protocol method."

## 2. Findings

| Id | Priority | Summary | Evidence |
|---|---|---|---|
| F-`<round>`-1 | P0 / P1 / P2 / P3 | `<one-line summary>` | `<file:line + grep proof OR ./scripts/dev.sh ... output>` |
| F-`<round>`-2 | ... | ... | ... |

If no findings: state "No findings."

## 3. Lesson codification result

Apply the protocol from `lesson-codification-protocol.md`. Output one of:

- **Streak advance**: `<lesson-id>` advances to streak `N-of-N`. The novel preservation type observed this round is `<type>` (first-seen ↔ `<round-id>`).
- **Streak break**: `<lesson-id>` streak broken at `N`; root cause: `<description>`. The lesson itself needs amendment OR a new lesson splits off.
- **No applicable lesson**: this round didn't exercise any tracked lesson. (Lessons only track recurring patterns.)
- **Propose new mandate**: the 3rd observation of `<pattern>` was seen this round. Propose mandate `<id>`.

## 4. Mistake-pattern checks

| Pattern | Applied? | Result |
|---|---|---|
| Fix-example-vs-contract | (only if fix-round) | PASS / FAIL with evidence |
| Sibling-doc-sweep | (only if round edited canonical docs) | PASS / FAIL with sibling list grep-quoted |
| Doc-vs-impl re-grep | (always when claims about impl are in handoff) | PASS / FAIL per claim |

## 5. Reference scan compliance

For every reference cited in the round (handoff § Reference triplet section):

| # | 用了哪个 (Which) | 为什么用 (Why) | 用了什么部分 (What part) | NOT used |
|---|---|---|---|---|
| 1 | `references/<repo>/<file>:<line-range>` | `<specific problem solved>` | `<exact extracted shape>` | `<what was deliberately not used>` |

Confirm each row is fully populated (no empty cells). Confirm reference tier (RT0/RT1/RT2/RT3) is declared.

## 6. Cross-mandate compliance

For every standing mandate from project CLAUDE.md / AGENTS.md:

| Mandate | Honored? | Evidence |
|---|---|---|
| `<mandate-id-or-name>` | YES / NO | `<grep proof or audit-fact reference>` |

## 7. Fact table

**Schema reminder**: every fact has an exact expected value (no `≥ N` or `> 0` patterns). Every command starts with `cd`, `git`, `uv run`, or `bash` (per `audit_check.py` parser-recognition contract, generalized).

| # | Fact | Command | Expected | Actual |
|---|---|---|---|---|
| 1 | Handoff exists | `git cat-file -e <handoff-commit>:<handoff-path>` | exit 0 | exit `<actual>` |
| 2 | All dev commits resolve | `cd <project> && git log <commit-range> --oneline \| wc -l` | exact N | actual M |
| 3 | Test count | `cd <project> && bash <test-command>` | exact "N passed" | actual |
| 4 | Spec claim grep | `awk -v s='<verbatim impl substring>' 'index($0,s){n++} END{print (n>0)?1:0}' <path>` | `1` | actual |
| ... | ... | ... | ... | ... |

**Sub-total:** N/N facts PASS (must equal N/N for outcome=PASS)

## 8. Forward-debt observations

Anything noticed during audit that's OUT OF SCOPE for this round but worth tracking:

- D-`<round>`-1 (P2/P3): `<description>` — owner: `<future round / phase>`
- ...

These get appended to `<project>/docs/tech-debt.md` (or equivalent) by the founder or next planner, not by the auditor directly.

## 9. Author's note (optional)

Free-form auditor commentary on the round's quality, trends, or recommendations for the next round. Cannot influence PASS/NEEDS_FIX outcome (those are mechanical).

---

**Verdict line (mandatory final paragraph):**

> Outcome: PASS / NEEDS_FIX. Audited dev commits: `<sha40>`…`<sha40>`. Fact table: N/N PASS. Findings: <count> P0+P1, <count> P2, <count> P3.
```
