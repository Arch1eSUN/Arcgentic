# Gate 3 (Cross-project) Protocol

**Status:** Deferred — Gate 3 itself is NOT run as part of v0.1.0-alpha.2 MVP. This protocol document establishes the procedure for future invocation, before promoting the plugin to v1.0.0 stable.

## Purpose

Verify arcgentic works on a project that does NOT have Moirai's specific infrastructure (no `./scripts/dev.sh`, no Obsidian vault, no Phase numbering, no 16+ fact-shapes). The goal: catch Moirai-isms that snuck into "generic" plugin code and would surprise a clean-slate user.

## Candidate projects

Pick ONE:
- Any of founder's other Arc Studio projects (Argus LLM / ConShellV2 / Giglio 2 / Poster) — known infrastructure, easy to set up.
- A public OSS repo cloned locally (e.g. a small Python or TypeScript library).
- A greenfield throwaway project (`mkdir + git init + sample code`).

## Protocol

1. **Initialize**:

   ```bash
   cd <candidate-project>
   bash $PLUGIN_ROOT/scripts/state/init.sh \
     --project-root . \
     --project-name "<name>" \
     --round-naming "<convention>"
   ```

2. **Verify no Moirai-isms in state.yaml**: the generated `state.yaml` should NOT reference `phase` / `Pythia` / `Moirai`. If it does, that's a portability bug — file as P1 in arcgentic's tech-debt.

3. **Run a trivial round** (similar to Gate 2's `v0.1.0-alpha.2-meta`): walk `intake → planning → ... → closed`. Use a 1-commit dev scope so the round is auditable in minutes.

4. **Verify universal compatibility**:
   - All transitions work without project-specific scripts (no `./scripts/dev.sh` calls)
   - All 3 MVP gates work without project-specific tooling (only Bash + Python3 + PyYAML + jsonschema)
   - `state.yaml` stays schema-valid throughout (validate via `bash $PLUGIN_ROOT/scripts/state/validate-schema.sh ./.agentic-rounds/state.yaml`)
   - `audit-round` skill produces a verdict using only the universal templates (no hardcoded Moirai mandate ids / Phase numbering / R10-L3 vocabulary)

5. **Record failures**: any breakage that implicitly required Moirai infrastructure → P1 portability bug filed in arcgentic's `docs/tech-debt.md`.

## Specific portability checks (run during Gate 3)

For each item below, verify arcgentic operates correctly without the project having it:

| Moirai infrastructure | arcgentic should work without it |
|---|---|
| `./scripts/dev.sh audit-check` | YES — `audit-round` skill should describe how to verify facts without this command (e.g. just `bash` per-fact) |
| Obsidian vault for mandate storage | YES — mandate references should point to project's CLAUDE.md / AGENTS.md only |
| Phase X / Phase X.Y numbering | YES — `state.yaml` `project.round_naming` is free-form; no hardcoded "phase" in plugin |
| Specific lesson ids (Lesson 8, Lesson 15) | YES — lesson catalog accumulates per-project; plugin should not reference "Lesson 8" by id in generic skills |
| `audit_check.py` parser-recognition prefix rules | YES — referenced as portable rule (Bash/git/uv-run/bash command prefixes) in `fact-table-design.md`, NOT as hardcoded Moirai script call |
| 4-commit chain convention (entry-admin / BA design / dev-body / state-refresh) | YES — `expected_dev_commits` in state.yaml is per-round-configurable; default not assumed to be 4 |
| 16-section handoff convention | YES — `sections_required` is per-round-configurable; default not assumed to be 16 |

## When to run

Before declaring arcgentic v0.1.0 stable (i.e. removing the `-alpha` tag).

## Expected duration

~1-2 hours including running the trivial round end-to-end on the candidate project. Most time is in step 4 (verification) — about 30 min per cross-cutting check.

## Record file

After the run, write `tests/dogfood/gate-3-cross-project/RESULT-<project-name>.md` with:
- Project name + brief description (language / size / type)
- Run date
- Outcome: PASS / FAIL
- Portability bugs found (with proposed fixes — exact file:line where Moirai-ism snuck in)
- Suggestions for `audit-round` references that need cross-project re-grounding

## Triple-candidate acceptance

Gate 3 PASS is defined as "PASS on 2 of 3 candidate projects across at least 2 language ecosystems (e.g. one Python + one TS + one Go)." A single project pass is insufficient — the goal is catching Moirai-isms which only surface across different ecosystems.

## Relationship to v1.0.0 stable

When Gate 3 has 2-of-3 PASS results recorded, arcgentic is eligible for:
- Removing `-alpha` from version
- Submitting to Claude Code plugin marketplace
- `v1.0.0` tag

Until Gate 3 has been run, arcgentic stays in `0.x.y-alpha` versions regardless of feature completeness.
