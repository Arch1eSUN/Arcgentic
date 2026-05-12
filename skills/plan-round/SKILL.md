---
name: plan-round
description: Use when starting a new round (substrate-touching / fix-round / admin) to generate a complete handoff doc from scope + prior-round context. Dispatches the planner sub-agent and validates output before writing.
---

# plan-round

Generates a round handoff at `docs/superpowers/plans/{YYYY-MM-DD}-{round_name}-handoff.md` by
dispatching the `planner` sub-agent with a self-contained brief, then validating its output
against the corresponding handoff template (18 / 12 / 10 section).

## When to invoke

- User says "let's plan R{N}" or "create handoff for R{N}"
- User runs `/plan-round` slash-command
- A new round-name appears in conversation without a corresponding handoff doc

## Prerequisites

Requires the `arcgentic` CLI installed (the Python toolkit):

- Stable: `pipx install arcgentic` (post-v0.2.0 PyPI release)
- Dev (in this repo): `cd toolkit && pip install -e ".[dev]"`

The CLI runs in a subprocess; this markdown skill is the thin shim that invokes it.

## Inputs

Parse from `$ARGUMENTS` (passed by Claude Code):

- `round_name` — e.g. "R10-L3-aletheia" or "R1.6.1"
- `round_type` — one of: substrate-touching | fix-round | entry-admin | close-admin | meta-admin-sweep
- `prior_round_anchor` — full 40-char SHA of prior round's last commit
- `scope_description` — optional 1-3 sentence scope (can be filled later in handoff)

If any required input is missing, ASK the user before proceeding.

## Workflow

When invoked with all inputs:

1. Validate `round_name` matches the pattern `R<phase>[.<round>[.<fix>]]` or `R<phase>-<name>`.
2. Validate `prior_round_anchor` is a full 40-character hex SHA (NOT short).
3. Shell out to the CLI:

   ```
   arcgentic plan-round-impl \
     --round=<round_name> \
     --type=<round_type> \
     --anchor=<prior_round_anchor> \
     --scope=<scope_description>
   ```

4. Read the CLI's stdout — it contains either:
   - `plan-round succeeded: wrote <path>` + section_count + loc + (optional) warnings
   - `FAILED: <error>` (exit code 1 or 2)

5. Report to the user: handoff path, section count, any warnings.

6. If validation failed (exit code 1 or 2): explain the failure + suggest a fix
   (re-run with correct anchor, etc.).

## Failure modes

- **Missing args**: ask the user.
- **CLI not installed**: instruct user to `pipx install arcgentic` or `pip install -e toolkit/`.
- **CLI returns FAILED with TBD/TODO/XXX warning**: this is the planner self-check working —
  the planner's output had unfilled placeholders. Re-run with more specific `--scope=...`
  OR open the handoff file at the reported path and fill the placeholders manually.
- **Section count mismatch**: the planner produced wrong number of sections. Possible causes:
  template files (templates/handoff_*) updated but skill cache stale — surface as a bug.

## See also

- `agents/planner.md` — the sub-agent dispatched by this skill (defines the planner's role + output contract)
- `templates/handoff_18_section.md` / `handoff_12_section.md` / `handoff_10_section.md` — section templates
- `toolkit/src/arcgentic/skills_impl/plan_round.py` — Python algorithm (full validation logic + adapter dispatch)
- spec § 4.1 — full algorithm specification
- spec § 5.1 — planner agent contract
- spec § 7 — handoff doc templates (authoritative)
