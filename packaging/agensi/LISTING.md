# Agensi listing copy

Copy for the free Agensi listing. Upload artifact:
`packaging/agensi/dist/arcgentic-agensi.zip` (SKILL.md + LICENSE at the root).

Rebuild the zip after editing `arcgentic/SKILL.md`:

```bash
cd packaging/agensi && rm -rf dist && mkdir dist && cp ../../LICENSE arcgentic/ && (cd arcgentic && zip -X -q ../dist/arcgentic-agensi.zip SKILL.md LICENSE) && rm arcgentic/LICENSE
```

## Title

Arcgentic: plan, build, and audit gates for coding agents

## Price

Free

## Short description

Gated plan → development → self-audit → external audit workflow for Codex and Claude Code, so AI-written code only counts as done with evidence.

## Long description

Arcgentic is an open-source (MIT) harness-engineering layer for Codex and Claude Code. AI coding sessions drift: scope changes silently, context gets lost, tests get skipped, and "done" often means "the assistant said it is done." Arcgentic wraps the agent in roles, handoffs, audits, and pass/fix gates so a round of work only closes when there is evidence.

How a round works:

1. Planner turns the idea into a scoped handoff.
2. Developer implements it and writes a self-audit.
3. Test (optional) runs a realistic user test.
4. Auditor reviews independently and returns PASS or a fix list.
5. The round closes only on PASS; otherwise it loops back.

This listing is the entry skill. It explains when Arcgentic fits and how to install the full plugin, which ships its own skills, agents, hooks, a Python CLI, and an optional MCP status panel. The full workflow runs in Codex and Claude Code.

Best for heavy Codex / Claude Code users, agent builders, and AI-native teams doing multi-round engineering work. Not meant for one-line edits or quick experiments.

- GitHub: https://github.com/Arch1eSUN/Arcgentic
- PyPI: https://pypi.org/project/arcgentic/
- npm: https://www.npmjs.com/package/arcgentic

## Tags

claude-code, codex, code-review, software-audit, workflow, ai-coding-agents, developer-tools, mcp

## Compatible agents

Claude Code, Codex
