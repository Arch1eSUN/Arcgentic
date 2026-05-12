---
name: pre-round-scan
description: Mandatory prelude for every role at the start of a round. Inventories available skills, MCP servers, plugins, sub-agents, and external references. Outputs which tools will be used in this round and which were considered but rejected, with reasons. Use as the very first action of every role skill in an arcgentic-managed project.
---

# Pre-round scan

## When to use

EVERY role skill (`plan-round`, `execute-round`, `audit-round`, `track-refs`) invokes this as its first action, before any other reasoning. Output goes into the role's handoff/verdict document as a "§ Toolkit use" section.

## Rationale

R1.4 Moirai mandate (post-NEEDS_FIX): "default: multi-agent dispatch is the path, serial is the exception". Without a pre-round scan, agents repeatedly forget that MCP servers / agency-agents / skills exist and default to from-scratch implementation. The scan is mechanical insurance.

## Procedure

1. **Read state.yaml** to know which round + which role
2. **Inventory locally available**:
   - Skills under `~/.claude/skills/` (user-level)
   - Plugins under `~/.claude/plugins/` (cached + installed)
   - MCP servers configured in `~/.claude.json`
   - Sub-agents under `~/.claude/agents/`
3. **Inventory project-local**:
   - Project's CLAUDE.md / AGENTS.md mandates
   - Project's `references/INDEX.md` (if exists) — categorized OSS clones
   - Project's tech-debt registry (if exists)
4. **Map to round needs**:
   - For each round-relevant subsystem, identify candidates from inventory
   - State which will be used + why
   - State which were considered + rejected + why
5. **Document in audit/handoff § "Toolkit use"**

See `references/scan-checklist.md` for the explicit checklist.

## Mandatory output format

```markdown
### Toolkit use (pre-round scan)

**Skills available + considered:**
- arcgentic:foo — used (reason)
- arcgentic:bar — rejected (reason)
- ...

**MCP servers available + considered:**
- context7 — used for {library} docs lookup
- ...

**Sub-agents available + considered:**
- backend-architect — used for BA design pass
- ...

**External references available + considered:**
- references/X — used (used-what-part)
- references/Y — rejected (reason)
- ...
```

## Failures count

Tool failures are first-class. If `context7` returns 500 and you fall back to web search, record both the attempt and the fallback. Silent degradation is a Rule 2 violation in arcgentic's discipline ledger.

## See also

`references/scan-checklist.md` — explicit checklist
