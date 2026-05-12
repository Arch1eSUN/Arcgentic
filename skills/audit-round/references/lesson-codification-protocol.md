# Lesson codification protocol

## Premise

Most LLM-assisted dev rounds discover lessons. Most of those lessons evaporate when the session ends. The codification protocol turns transient lessons into durable mandates.

Generalized from Moirai's "Lesson 8 STRUCTURAL-LAW codification" (streak 10-of-10 with novel preservation types). The pattern is universal; the names (Lesson 8 / Phase 10 / R10-L3) are not — projects accumulate their own catalog.

## The cycle

```
observe → infer → verify → encode → declare
   ↑                                    │
   └────────── (next round) ────────────┘
```

### Step 1 — Observe (during audit)

Auditor notices a pattern across rounds. Examples:
- "Three consecutive fix rounds repeated R1.3.1 shape" (fix the example, miss the contract)
- "Every round that touches reference X uses 4-column triplet" (positive pattern)
- "Audit-fact commands without revision boundary keep returning wrong answers" (negative pattern, governance)

### Step 2 — Infer

Articulate the **architectural shape** of the pattern. NOT the specific Moirai-vocabulary description — strip vocabulary, keep architecture.

Bad inference (Moirai-specific):
> "R1.3.1 shape: fixing the negative-int case but not the non-negative-integer contract."

Good inference (portable):
> "When fixing an issue, write tests against the contract's full input domain, not just the auditor's reproducer."

### Step 3 — Verify

For each observation, demonstrate the inference holds. Run the inferred check against the prior commit that exhibited the pattern, AND against the current commit being audited.

```bash
# Example: verify the doc-vs-impl re-grep inference would have caught the bug
git diff <bad-commit>..<good-commit> -- <doc-file> | grep <impl-symbol-that-was-stale>
# Expected: lines showing the bug existed in <bad-commit>
```

If verification fails (the inference doesn't actually predict the bug), iterate: re-observe, re-infer.

### Step 4 — Encode

Once verified, encode as one of:

**(a) Streak iteration** — observation matches an existing lesson. Update the lesson's streak count + record the novel preservation type observed this round.

```yaml
lessons:
  - id: "lesson-8"
    name: "codification-system-universality"
    streak: 10                              # +1 from previous
    novel_types_seen:
      - { type: "scope-reduction", first_seen: "R10-L1-..." }
      - { type: "multi-source", first_seen: "R10-L2-..." }
      - { type: "layer-transition", first_seen: "R10-L3-llm" }  # NEW this round
    last_application: "R10-L3-llm"
```

**(b) New lesson** — observation is novel. Add a new lesson entry.

```yaml
lessons:
  - id: "lesson-N+1"
    name: "<inferred-architectural-shape>"
    streak: 1
    novel_types_seen: [{ type: "<this-round's-type>", first_seen: "<round-id>" }]
    last_application: "<round-id>"
```

**(c) Mandate proposal** — observation is the **3rd** instance of a recurring negative pattern. Time to write a rule.

```markdown
## Mandate proposal: <id> — <one-line description>

Observed in: <round-1-id>, <round-2-id>, <this-round-id>

Rule: <prescriptive form, ideally with a mechanical check>

Mechanical check (audit-fact-shape):
```bash
<command that detects future occurrences>
```

Forward owner: <project phase or "any round">

Acceptance criteria: <when can this mandate be retired>
```

### Step 5 — Declare

In the verdict's § 3 (Lesson codification result), write one of:

- "Streak advance: lesson-N advances to streak K-of-K with novel `<type>` preservation."
- "New lesson: lesson-N+1 (`<shape>`) recorded at streak 1."
- "Mandate proposal: `<id>` ready for founder acceptance."
- "No applicable lesson this round." (acceptable; not every round triggers codification)

## When NOT to codify

- **Once-off** patterns — don't mandate a single-occurrence fix
- **External constraints** — if the pattern is caused by an OSS dep behavior we don't control, document but don't mandate
- **Conflicts with existing mandate** — surface conflict to founder, don't quietly override

## Anti-patterns (do not do)

- **Vocabulary preservation** — codifying "R1.5d-chain" by name. The chain is Moirai-specific; the *pattern* (sibling-doc sweep) is universal. Codify the pattern, mention the chain as example.
- **Over-codification** — every minor observation becomes a mandate. Cap: max 1 new mandate per round; max 1 new lesson per round.
- **Codification without verification** — proposing a mandate without running Step 3. Mandates without empirical grounding are noise.

## NOVEL preservation types

The phrase "novel preservation type" refers to a kind of *thing the lesson preserved across observations*. Examples from Moirai:

- `scope-reduction` — the round demonstrated scope-reduction discipline (lesson applied while halving original scope)
- `multi-source` — the round demonstrated multi-source vendor pattern (lesson applied while introducing new vendor structure)
- `layer-transition` — the round demonstrated layer-transition (L2 substrate → L3 substrate) preservation (lesson applied across architectural layer boundary)

Each is a "shape of round" the lesson survived. Projects accumulate their own NOVEL types as their architecture evolves.

## Output to state.yaml

After verdict commit, update `lessons[]` in state.yaml. The lesson-codifier sub-agent (post-MVP) automates this; in MVP, the auditor does it manually:

```bash
# Manual update via yaml_set helpers (after verdict commit)
source $PLUGIN_ROOT/scripts/lib/yaml.sh
yaml_set <project>/.agentic-rounds/state.yaml \
  "lessons.0.streak" "10"
yaml_set <project>/.agentic-rounds/state.yaml \
  "lessons.0.last_application" "<round-id>"
```

(For appending a novel type, use `yaml_append_to_list`.)

## Anchor

This protocol's first concrete validation: Moirai project R10-L3-llm verdict, streak 10-of-10 with novel `layer-transition` preservation type. The fact that the protocol *works* in a real project is its claim to portability — not theoretical justification.
