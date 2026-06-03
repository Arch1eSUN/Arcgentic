---
name: codify-lesson
description: Detect recurring P2/P3 audit patterns across recent rounds and promote them into lesson cards. Use after round boundaries or when repeated findings appear.
---

# codify-lesson

Scans recent audit handoffs for recurring P2/P3 patterns in structured findings
tables and promotes repeated clusters into lesson cards.

## When to invoke

- After `round-boundary-lesson-scan` reports a promotable cluster
- User invokes `/codify-lesson`
- 3+ rounds show the same structured finding pattern

## Workflow

1. Shell out to the toolkit:

   ```bash
   arcgentic codify-lesson \
     --audit-dir docs/audits \
     --lessons-dir lessons \
     --amendments-dir mandates/amendments
   ```

2. Read stdout:
   - `lessons: N`
   - `amendments: N`
   - `streak_updates: N`

3. Inspect every generated lesson card before accepting it.

4. If an amendment proposal is generated, stop for founder review before applying
   mandate/rule changes.

The scanner ignores reference scans, author notes, forward-debt prose, and other
unstructured markdown even when those sections mention `P2` or `P3`.

## Output contract

- New lesson card: `lessons/lesson-{N}-{slug}.md`
- Formal-threshold amendment proposal: `mandates/amendments/amendment-{slug}.md`
- Existing lesson streak updates when a lesson was preserved

## See also

- `agents/lesson-codifier.md`
- `toolkit/src/arcgentic/skills_impl/codify_lesson.py`
- `toolkit/src/arcgentic/utils/pattern_detection.py`
