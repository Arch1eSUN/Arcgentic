# Pre-round scan: explicit checklist

Run this end-to-end at the start of every round. Output goes into the role's audit/handoff `§ Toolkit use` section.

## 1. State context
- [ ] Read `.agentic-rounds/state.yaml`. Note `current_round.id`, `current_round.state`, `project.round_naming`.
- [ ] Read project CLAUDE.md / AGENTS.md. Note any standing mandates that apply this round.

## 2. Local Claude Code inventory
- [ ] `ls ~/.claude/skills/` — note skills potentially relevant by name match to the round scope
- [ ] `cat ~/.claude/plugins/installed_plugins.json` — note plugin packages active
- [ ] `cat ~/.claude.json | jq .mcpServers` — note MCP servers
- [ ] `ls ~/.claude/agents/` — note agent personas

## 3. Project inventory
- [ ] If `<project>/references/INDEX.md` exists → grep by round-scope keywords. List matches.
- [ ] If `<project>/docs/tech-debt.md` exists → grep by round-scope keywords. List blocking debts.

## 4. Map → round needs
For each candidate from steps 2–3, classify:
- **Used** (with reason — which subsystem it serves)
- **Considered but rejected** (with reason — why not)
- **Used as fallback** (when primary tool failed)

## 5. Cost-discipline cross-check
- [ ] Does any candidate tool issue paid-API calls? If yes → reject + state alternative.
- [ ] Does any candidate run a background process / daemon? If yes → reject.

## 6. Output the scan to the round's handoff/verdict doc
Use the format from `SKILL.md § Mandatory output format`.

## Common rejection reasons (template-quotable)
- "Considered context7 for X library docs; rejected because the library is internal-only."
- "Considered playwright MCP; rejected because the round has no UI scope."
- "Considered the openai SDK reference; rejected because it would consume founder's API quota at runtime (§ 4 cost-discipline ban)."
