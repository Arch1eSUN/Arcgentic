# Fact table design

## Why fact tables

Every claim in a round (scope met, sections present, tests pass, mandates honored) must be MECHANICALLY VERIFIABLE — meaning a Bash command produces the answer, and the answer matches the expected value EXACTLY.

Without mechanical verification, audit verdicts become opinion. With it, they become contracts the round signed.

## Fact anatomy

A fact is a row with 5 columns:

```
| # | Fact | Command | Expected | Actual |
```

- `#` — monotonic number within this verdict
- `Fact` — one-line description of what's being verified
- `Command` — a Bash one-liner that produces the answer to stdout (or sets exit code)
- `Expected` — the exact string / number / exit code the command should produce
- `Actual` — left blank in the draft; filled in when the auditor runs the command

## Design rules

### Rule 1 — Command starts with `cd`, `git`, `uv run`, or `bash`

This matches the typical project-side `audit_check.py` parser recognition (generalized from Moirai R1.5c.5 lesson). Commands starting with other prefixes (e.g. raw `awk`, `python`, `grep`) confuse automated fact-table runners.

**Workaround for awk-on-file**: prefix with `cd "<project-root>" && `. The `cd` is a no-op for awk reading absolute paths but satisfies the parser gate.

✓ `cd /path && git log -1 --grep='X' <SHA40> --format=%H`
✓ `bash -c "awk -v s='X' 'index(\$0,s){n++} END{print (n>0)?1:0}' file"`
✓ `uv run pytest tests/ -k test_x -q --tb=line`
✗ `awk -v s='X' 'index(\$0,s){n++} END{print (n>0)?1:0}' file` (raw awk, parser-rejected)

### Rule 2 — Expected value is exact

No `≥ N`, no `> 0`, no "approximately", no regex like `/pass/i`. EXACT.

✓ Expected: `15`
✓ Expected: `1`
✓ Expected: `0`
✓ Expected: `15 passed, 0 failed`
✗ Expected: `≥ 15`
✗ Expected: `> 0`
✗ Expected: `at least one match`

Auditing tools that DO support range expectations are great, but they ALWAYS reduce to exact comparisons internally. The fact-table form is the exact form.

### Rule 3 — `git log --grep` queries MUST include a revision boundary

Without a boundary, the walk includes every future commit added to main, so the answer drifts. With a boundary, the walk is `<boundary>..<root>` (the boundary commit and its ancestors only) — descendants are invisible, the answer is immutable.

✓ `git log -1 --grep='round-X' <SHA40> --format=%H`
✗ `git log -1 --grep='round-X' --format=%H` (unbounded — answer drifts)

Same applies to `git log --author`, `git rev-list --grep`, and any free-text moving-target query.

### Rule 4 — Every fact is independently runnable

The auditor must be able to copy-paste a single fact's command and get its answer. No fact may depend on state from a previous fact's command execution. If you need staged state, materialize it via a setup step in fact #0 (and verify the setup step itself succeeds).

### Rule 5 — Failure mode is part of design

For every fact, write down what would cause it to fail and what fixing it would look like. If you can't name a plausible failure mode, the fact isn't testing anything real (delete it).

### Rule 6 — Minimum fact count by round size

- Round with 1 sub-task: ≥ 5 facts
- Round with 2-4 sub-tasks: ≥ 10 facts
- Round with 5+ sub-tasks: ≥ 15 facts
- Any round touching docs+impl: ≥ 1 doc-vs-impl re-grep fact per affected canonical doc

## Mandatory mechanical fact-shapes (project-extensible)

The plugin ships with **0** required fact-shapes — it's up to each project to accumulate its own. But the SHAPES below are commonly useful starting points:

### Shape A: "claim N matches reality"

Auditor claims "N tests pass." Fact:
```
| 1 | All tests pass | cd <project> && bash test.sh | grep -c "passed" | 15 |
```

### Shape B: "file X exists at commit Y"

Auditor claims "handoff doc was committed at SHA Z." Fact:
```
| 2 | handoff committed | git cat-file -e <SHA>:<path> 2>&1 ; echo $? | 0 |
```

### Shape C: "doc claim grep-quotes impl"

Auditor claims handoff § 5 says X. Fact:
```
| 3 | doc claim grounded | cd <project> && awk -v s='<verbatim impl substring>' 'index($0,s){n++} END{print (n>0)?1:0}' <impl-file> | 1 |
```

### Shape D: "mandate honored"

Auditor claims "round did pre-round scan." Fact:
```
| 4 | pre-round scan present | grep -c "Toolkit use" <handoff-doc> | 1 |
```

### Shape E: "fix-round only touches in-scope files"

Auditor claims "fix-round narrow." Fact:
```
| 5 | fix-round narrow | cd <project> && git diff --name-only <prior-SHA>..<this-SHA> | wc -l | 7 |
```

### Shape F: "no banned pattern in diff"

Auditor claims "no paid-API calls added." Fact:
```
| 6 | no paid-API | cd <project> && git diff <prior>..<this> | grep -cE "openai\.|anthropic\.|claude api|API_KEY" | 0 |
```

## Adding a project-specific fact-shape

When the same audit fact pattern appears 3 times across rounds, codify it as a project fact-shape:
1. Add `mandatory mechanical fact-shape #N: <description>` to project CLAUDE.md
2. Cite by `#N` in subsequent verdict fact-table rows
3. (Optional) Add the shape's command template to project's `audit-fact-shapes.md` so it's grep-discoverable

This is the **lesson codification protocol** (Lesson 8 generalized — see `lesson-codification-protocol.md`) applied specifically to fact-shapes.
