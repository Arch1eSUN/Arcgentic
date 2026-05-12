# {ROUND_UPPER}_BA_DESIGN

**Round**: {round_name} (e.g. R10-L3-aletheia → uppercased: R10_L3_ALETHEIA)
**Type**: BA design pass for substrate-touching round (or fix-round / admin if applicable)
**Mandate posture**: Mandate #17(d) FULL-STRENGTH; clause (h) Option A {Nth} round
**Authoring agent**: ba-designer (arcgentic v{VERSION})
**Date**: {YYYY-MM-DD}

---

## § 0. Round Context — Why {round_name} Is Inserted Here

{1-2 paragraphs: what gap this round fills in the project arc; cite prior rounds + forward-debts
this round addresses; cite handoff § 1 scope statement}

## § 1. Reference Scan (mandate § 8.12 (a) + (e) + RT vocab #13 (h))

{5-column triplet table; at least 1 row}

| # | Reference | Why used | What part | License + RT tier |
|---|---|---|---|---|
| 1 | {ref-name (repo / paper / doc)} | {1-sentence rationale} | {pinpoint extracted shape: function / pattern / API / data model} | {license: MIT/Apache/AGPL/BSD/etc} + RT{0/1/2/3} |

(RT0 = PATTERN-only / RT1 = source-adapt / RT2 = binary vendor / RT3 = full runtime dep — per spec § 1.4 + § 12)

## § 2. BA-numeric-claim-snapshot-verify (mandate #24 EXTENSION — {Nth} application)

### 2.1 Baseline (current state — before this round)

{Numeric snapshot table:}

| Metric | Pre-round value |
|---|---|
| Total LOC ({lang}) | {N} |
| Source files | {N} |
| Test files | {N} |
| Test assertions / `assert` count | {N} |
| Mypy --strict errors | {N — expect 0} |
| Forward-debts aggregate | {N} |
| Lesson 8 streak | {N}-of-{N} ({preservation_type}) |

### 2.2 Projected deltas (after this round)

| Metric | Post-round projection | Net change |
|---|---|---|
| Total LOC | +{N} ~ {projected_total} | +{N} |
| Source files | +{N} ~ {projected_total} | +{N} |
| Test files | +{N} ~ {projected_total} | +{N} |
| Test assertions | +{N} ~ {projected_total} | +{N} |
| Mypy --strict errors | 0 (must remain) | 0 |
| Forward-debts | +{N_new} -{N_resolved} = {net} | {net} |
| Lesson 8 streak | {N+1}-of-{N+1} ({preservation_type}) | +1 |

## § 3. Substrate Architecture — {Main module / Top-Level}

### 3.1 Decision D-1: {decision_title}

**Decision**: {1 sentence}.

**Rationale**:
1. {constraint or requirement cited from handoff / prior round / external reference}
2. {...}
3. {...}

**Alternatives rejected**:
- **Alt A: {name}** — rejected because {reason}.
- **Alt B: {name}** — rejected because {reason}.

### 3.2 Decision D-2: {decision_title}

**Decision**: {1 sentence}.

**Rationale**:
1. {constraint or requirement cited from handoff / prior round / external reference}
2. {...}
3. {...}

**Alternatives rejected**:
- **Alt A: {name}** — rejected because {reason}.
- **Alt B: {name}** — rejected because {reason}.

### 3.N Decision D-N: {decision_title}

(Typical substrate round has 3-7 named decisions D-1..D-N.)

**Decision**: {1 sentence}.

**Rationale**:
1. {constraint or requirement}
2. {...}

**Alternatives rejected**:
- **Alt A: {name}** — rejected because {reason}.

## § 4. {Feature/Module 2} (if applicable)

{Same shape as § 3 — only for rounds delivering multiple substrate features.
Omit § 4..§ N-1 if round is single-substrate.}

### 4.1 Decision D-{M}: {decision_title}

**Decision**: {1 sentence}.

**Rationale**:
1. {...}

**Alternatives rejected**:
- **Alt A: {name}** — rejected because {reason}.

## § 5. {Feature/Module 3} (if applicable)

{Same shape as § 3 / § 4. Add or remove §§ 4..N-1 as needed for multi-substrate rounds.}

## § 6. File-Level Decomposition

{Every file this round creates or modifies, with type + estimated LOC:}

| File path | Type | Est. LOC | Purpose |
|---|---|---|---|
| {path/to/file.py} | source | {N} | {what it does} |
| {path/to/test_file.py} | test (unit / property / integration) | {N} | {what it tests} |
| {...} | {...} | {...} | {...} |

## § 7. Test Plan

{Coverage per file with focus area:}

| Test file | Tests | Coverage focus |
|---|---|---|
| {test_X.py} | {test_a, test_b, test_c} | {what aspect tested — happy path / edge cases / Protocol conformance / etc.} |

Every Protocol method MUST have at least 1 test. Every typed-error class MUST have a raises-test.

## § 8. Anti-scope Explicit

{What this design does NOT include with rationale. Mechanically verifiable via grep.}

- **NOT delivered**: {feature X} — rationale: deferred to round {Y}; out of scope for this round's substrate goal.
- **NOT delivered**: {feature Z} — rationale: blocked on prior decision; not yet justified.

## § 9. EventLog Event Surface (if applicable — substrate-touching rounds with new event classes)

{New EventLog event types this round introduces:}

| Event class | When emitted | Required fields | Replay determinism |
|---|---|---|---|
| {EventA} | {trigger condition} | {field list} | {deterministic / partial / non-deterministic with explanation} |

## § 10. Typed Errors

{Every typed-error class introduced by this round:}

| Error class | When raised | Where caught | Recovery behavior |
|---|---|---|---|
| {ErrorA} | {condition} | {catching function:line} | {what happens on catch} |

---

*BA design for {round_name} written by ba-designer agent (arcgentic v{VERSION}).*
