# Mistake pattern: fix the example, miss the contract

## Generalized from

Moirai R1.3 → R1.3.1 → R1.3.2 chain (2 consecutive NEEDS_FIX verdicts). R1.3.1 fixed the auditor's negative-int repro case but didn't generalize to the full non-negative-integer contract; R1.3.2 caught the gap.

## The pattern

When fixing an issue identified by an auditor:
1. **Bad mode**: fix exactly the reproducer the auditor cited; ship.
2. **Good mode**: identify the **contract's full input domain**; write tests for the full domain; fix to satisfy all of them; ship.

The "contract" is the Protocol / interface / function signature / class invariant the bug violates. The "example" is the one input the auditor happened to try.

## Detection (audit check)

When a round is a fix-round (state was `needs_fix → fix_in_progress → awaiting_audit`):

1. Identify the auditor's original reproducer cases
2. Identify the Protocol / interface / function the reproducer violates
3. Enumerate the Protocol's full input domain (or representative cells)
4. Verify the fix-round's tests cover the full domain, not just the reproducer

### Mechanical fact (template)

```bash
| F | fix-round covers contract domain | cd <project> && grep -l "<protocol_method>" tests/ | xargs grep -l "<full-domain-cell-1>" -- ; grep -l "<protocol_method>" tests/ | xargs grep -l "<full-domain-cell-2>" -- | wc -l | 2 |
```

The expected value is the count of full-domain cells covered. If the fix-round only covers 1 (the reproducer), the test fails the gate.

## Detection (during round-writing)

For developers (in fix rounds): before writing the fix, enumerate the contract:

```
Protocol: <fully-qualified-name>
Method:   <method-signature>
Full input domain:
  - cell 1: <category, e.g. negative ints>
  - cell 2: <category, e.g. zero>
  - cell 3: <category, e.g. positive ints>
  - cell 4: <category, e.g. None>
  - cell 5: <category, e.g. extremely large ints>

Auditor's reproducer cited cell: <1>
Therefore tests for fix-round MUST cover: <1, 2, 3, 4, 5>
```

If the developer can't enumerate, the contract isn't clearly defined — escalate to planner to clarify before fixing.

## When this pattern DOESN'T apply

- Round is a feature-add (not a fix) — no auditor reproducer to expand
- Bug truly is single-cell (e.g. a typo in a literal); there is no broader domain
- Contract is by design narrow (single-cell input, e.g. `assert_eq_to_42()`)

## Generalized rule (mandate-quotable)

> When fixing an issue, write the test against the contract's full input domain, not just the auditor's reproducer. If you find yourself fixing exactly the auditor's repro case and nothing else, you're about to ship another fix round.

## Examples archive

- Moirai R1.3.1: contract `EventLog.read_since(offset)`, reproducer was `offset=-1`, full domain was `{negative, 0, positive < length, positive == length, positive > length, None}`. R1.3.1 fixed only `offset=-1`. R1.3.2 generalized.
- (Add project's own examples here as they accumulate.)
