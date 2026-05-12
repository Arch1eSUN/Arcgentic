# Sub-agent dispatch patterns

## Why dispatch sub-agents

Two reasons:
1. **Context isolation**: auditor must NOT read planner/developer reasoning. Sub-agent dispatch puts auditor in fresh context.
2. **Parallel work**: lesson-codifier + auditor can run concurrently (codifier scans prior rounds while auditor reads this round's inputs).

## Dispatch via Claude Code Task tool

```
Use Task tool:
  description: "<3-5 word description>"
  subagent_type: "general-purpose" (or platform-specific like "code-reviewer")
  prompt: |
    <self-contained brief>
```

The sub-agent inherits:
- No conversation history from the orchestrator
- Same tool access (Bash / Read / Write / etc.)
- Same skills + plugins
- Same MCP servers

The sub-agent returns:
- A single message back (its result)
- Side effects: files written, commits made, state.yaml updated

## MVP-supported dispatch (auditor)

**Prompt template** (paste into Task tool prompt field, replace `<...>`):

```
You are the auditor sub-agent for arcgentic round <round-id>.

CONTEXT YOU INHERIT:
- Plugin root: /Users/<...>/Desktop/Arc Studio/arcgentic/
- Project root: <project-root>
- State file: <project-root>/.agentic-rounds/state.yaml
- Round being audited: <round-id> at state audit_in_progress
- Handoff doc: <project-root>/<handoff-path>
- Dev commits (verify each resolves): <list of SHA40>

PROCEDURE:
1. Load skill: arcgentic:audit-round (read its SKILL.md fully + load references/ as needed)
2. Run pre-round-scan first
3. Follow audit-round procedure step by step
4. Produce verdict at: <project-root>/<audits-dir>/<round-id>-external-audit-verdict.md
5. Update state.yaml's current_round.audit_verdict block per schema
6. Verify your fact table by running every command

RETURN: A single message stating:
- "DONE — verdict at <path>, outcome <PASS|NEEDS_FIX>, <N>/<N> facts PASS, <count> findings (<P0>+<P1>+<P2>+<P3>)"
- OR "BLOCKED — <reason>" if you cannot complete

DO NOT:
- Read the developer's session transcript or planner's reasoning chain
- Call paid APIs
- Spawn background processes
- Trust your own success without running the fact-table commands
```

## Verifying the sub-agent output

After Task returns:

```bash
# 1. Check the verdict file was created
test -f "<project-root>/<audits-dir>/<round-id>-external-audit-verdict.md" || { echo "verdict not written"; exit 1; }

# 2. Check state.yaml updated
source $PLUGIN_ROOT/scripts/lib/yaml.sh
VERDICT=$(yaml_get "<project-root>/.agentic-rounds/state.yaml" "current_round.audit_verdict")
test -n "$VERDICT" && test "$VERDICT" != "null" || { echo "state.yaml not updated"; exit 1; }

# 3. Re-validate state.yaml schema
bash $PLUGIN_ROOT/scripts/state/validate-schema.sh "<project-root>/.agentic-rounds/state.yaml"

# 4. Run the gate
bash $PLUGIN_ROOT/scripts/gates/verdict-fact-table-gate.sh --state-file "<project-root>/.agentic-rounds/state.yaml"

# 5. If gate passes, transition
bash $PLUGIN_ROOT/scripts/state/transition.sh \
  --state-file "<project-root>/.agentic-rounds/state.yaml" \
  --target "passed" \
  --by "orchestrator" \
  --artifact "<verdict-path>"
```

If any step fails: do NOT auto-retry. Report to founder. Let founder decide.

## Post-MVP dispatch (planner / developer / lesson-codifier / ref-tracker)

These agents do not exist yet. Post-MVP plan adds them with the same dispatch pattern.

## When to NOT dispatch

- Round is trivial (e.g. typo fix in a doc); manual handling is faster than dispatching
- The orchestrator is already in the right role context (e.g. you loaded `audit-round` directly because you ARE the auditor session)
- Sub-agent failed previously and retry would be wasteful — escalate to founder
