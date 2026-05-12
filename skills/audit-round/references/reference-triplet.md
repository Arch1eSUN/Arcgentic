# Reference triplet (4-column citation format)

## When to use

Every external reference (OSS repo / paper / spec / SDK) cited in a round MUST be cited in the 4-column format. Goes in handoff `§ Reference triplet` AND in any tech-debt entry that fuses external code.

## 4 columns

| # | 用了哪个 (Which) | 为什么用 (Why) | 用了什么部分 (What part) | NOT used |
|---|---|---|---|---|
| 1 | `references/<repo>/<sub-path>/<file>:<line-range>` + `references/<repo>/LICENSE` | the specific problem this reference solves better than from-scratch (cite missing pattern / edge case / security property) — concrete, not "OSS prior art exists" | the exact extracted shape (regex / 5-line install pattern / function signature / layered diagram / specific algorithm / defensive convention) — pinpoint, not "general approach" | what was explicitly NOT used (and why) — proves the citation is bounded |

## Why this format

Auditing references without this format devolves into "we looked at lots of OSS code." With it, the audit can verify:
- The reference license is compatible (LICENSE path proves it)
- The reference actually solves the problem the round claims (Why column)
- Only the cited part was used (What part column)
- The unused parts were considered and excluded (NOT used column — closes vague-attribution risk)

## Examples

**Good (concrete)**:

| 1 | `references/letta/letta/utils.py:42-52` + `references/letta/LICENSE` (Apache-2.0) | letta has battle-tested Unicode identifier sanitization regex with surrogate-pair rejection that we need for SessionForked event ids; we lacked this pattern | the `_SURROGATE_RE = re.compile(r'[\uD800-\uDFFF]')` regex constant + the `is_identifier(s)` predicate | did NOT use the broader `Letta.Memory` system — only the regex + predicate |

**Bad (vague — will fail audit)**:

| 1 | letta | OSS prior art for Unicode handling | general approach | (empty) |

## Reference triplet → Reference tier

After citing the triplet, declare the **Reference tier** (RT0-RT3). See `rt-tier-taxonomy.md`.

## Audit fact (every round citing references)

```bash
| F | reference triplet 4-column complete | cd <project> && grep -A 100 "## Reference triplet" <handoff-doc> | grep -c "^| " | <exact-row-count> |
```

The row count must match the number of references cited in `§ 3 Reference scan` of the handoff.

## Generalized rule (mandate-quotable)

> Every external reference cited MUST document the triplet in handoff/verdict § Reference triplet and any tech-debt entry that fuses code. 4 columns: 用了哪个 / 为什么用 / 用了什么部分 / NOT used.
