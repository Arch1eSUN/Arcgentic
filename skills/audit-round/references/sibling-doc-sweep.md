# Mistake pattern: fix one doc, miss the sibling

## Generalized from

Moirai R1.5d → R1.5d.1 → R1.5d.2 → R1.5d.3 chain (3 consecutive NEEDS_FIX verdicts, all doc-vs-impl drift). R1.5d.1 fixed EVENT_LOG_CONTRACT but missed data-flow.md (sibling canonical doc); R1.5d.2 fixed § 2 enforcement order but missed § 2.1 typed-error claim; R1.5d.3 fixed both.

## The pattern

When editing a canonical doc / spec / contract / diagram:
1. **Bad mode**: edit the section pointed to by the bug; ship.
2. **Good mode**: identify ALL canonical docs that touch the same impl surface; apply the fix to each; verify cross-doc parity; ship.

The "impl surface" is whatever the docs are claiming (a Protocol method, an error class, a constant, a behavior). Multiple docs typically reference the same surface.

## Detection (audit check)

When a round edits any canonical doc:

1. Identify all docs that reference the same impl surface
2. For each sibling doc, verify it agrees with the canonical one
3. Cross-document parity is the safety net

### Mechanical fact (template)

```bash
| F | sibling-doc parity | cd <project> && diff <(grep -A 10 "<symbol>" docs/contracts/X.md) <(grep -A 10 "<symbol>" docs/architecture/Y.md) | head -1 | wc -l | 0 |
```

If `wc -l` returns 0, the two docs agree. If > 0, they disagree → drift.

## Detection (during round-writing)

Before editing a canonical doc, enumerate sibling docs:

```bash
# Find all docs that reference the same symbol
cd <project> && grep -rl "<symbol>" docs/ | sort -u
```

Apply the same edit to every match. Then run the parity check.

## Sibling-doc inventory pattern

A typical project has 3-tier doc hierarchy:
- **Contract docs** (`docs/contracts/`) — formal spec
- **Architecture docs** (`docs/architecture/`) — diagrams + design intent
- **Plan docs** (`docs/plans/`) — round-by-round handoff (less canonical)

Any change in tier 1 (contracts) almost always requires a parity check in tier 2 (architecture). Tier 3 is round-scoped and usually OK to leave with historical drift.

## When this pattern DOESN'T apply

- Round edits a tier-3 plan doc only (historical record, not canonical)
- Symbol referenced in only one doc (no sibling exists)
- Symbol intentionally inconsistent (e.g. "this is the v1 API, that's the v2 API")

## Generalized rule (mandate-quotable)

> When editing a canonical doc that claims something about impl, sweep ALL sibling docs that reference the same impl surface. Verify cross-doc parity via grep-quotable verification.

## 4-step discipline (mandatory before doc edit)

1. **Re-read the canonical impl source** — `grep -A 15 "<symbol>" <impl-file>`; verbatim-quote the actual signature/code
2. **Sweep the entire same-round doc-set** — apply the same fix to every doc touched in this round
3. **Sweep the entire impl-surface doc-set** — apply the same fix to every doc that references the same impl surface (regardless of when it was last edited)
4. **Write a runtime-verification audit fact** — `awk -v s='<verbatim impl substring>' 'index($0,s){n++} END{print (n>0)?1:0}' <doc-file>` → expect `1`

## Examples archive

- Moirai R1.5d.1: fixed EVENT_LOG_CONTRACT § 2.2 but missed data-flow.md append diagram (same architectural surface).
- Moirai R1.5d.2: fixed § 2 enforcement order narrative but missed § 2.1 typed-error claim (same § 2 surface).
- (Add project's own examples.)

## Related

`doc-vs-impl-regrep.md` — the re-grep discipline that this pattern relies on
