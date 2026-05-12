# Doc-vs-impl re-grep discipline

## Rule

> Before claiming what spec/contract/architecture doc X says about impl Y, re-read Y from source. Paraphrase from memory or design intent is banned. Every claim about impl must be grep-quotable from impl.

## Application

For every claim in a round's handoff / verdict / spec that references impl:
1. Identify the symbol (class / method / function / constant / behavior name)
2. Run `grep -A 15 "<symbol>" <impl-file>` against actual impl source
3. Verbatim-quote the actual signature/code into the doc
4. Verify the doc claim matches what you just grepped

## Mechanical fact (every doc-affecting round)

```bash
| F | spec claim grounded in impl | cd <project> && awk -v s='<verbatim impl substring>' 'index($0,s){n++} END{print (n>0)?1:0}' <doc-file> | 1 |
```

If `0` returned, the doc claims something that doesn't exist in impl → drift.

## When to apply

ALWAYS when:
- Writing a spec/contract claim about runtime behavior
- Writing a class diagram or sequence diagram referencing real methods
- Writing a "the system does X" statement that maps to impl

NEVER skip when:
- "I remember what it does" — memory is corruptible; re-grep
- "I'm writing the impl and the doc at the same time so they must agree" — they often don't; re-grep separately
- "This was true last round" — paraphrases drift between rounds; re-grep

## Anti-patterns

- Paraphrasing impl behavior in your own words ("the function returns the offset" — verify it returns exactly what)
- Quoting an older version of impl that you remember
- Citing a method signature that was renamed in a previous fix-round
- Describing default values without checking the impl's default

## Cost

Re-grepping is ~5 seconds per claim. Fixing a NEEDS_FIX caused by drift is ~hours. The cost-discipline trade is obvious.
