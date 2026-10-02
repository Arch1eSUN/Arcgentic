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

## Submitted listing (2026-10-02)

Submitted for review on 2026-10-02 as a free listing. Agensi auto-generates most of the
listing from the zip (block description, demo session, tags, permissions, FAQ). These
auto-generated claims were wrong and were corrected before submission. Re-check them
whenever the zip is re-uploaded:

- Permissions: auto-detect ticked **Terminal / Shell**; the entry skill runs no commands,
  so only **Read Files** is ticked (it checks whether the plugin is installed).
- FAQ "what is included": claimed a "proprietary harness configuration". It is MIT and free,
  and the package is only SKILL.md + LICENSE.
- FAQ "is install automated": claimed the CLI "installs the necessary Node.js plugins". The
  user runs the install commands; nothing is installed without their go-ahead.
- FAQ "updates": claimed updates come through Agensi. The plugin updates via the Claude Code
  plugin marketplace, npm, and PyPI; only this entry skill updates on Agensi.
- Frameworks text: claimed Node.js is needed for plugin management. Only the Codex npm
  install needs Node.js 18+; the CLI and MCP panel need Python 3.13+.
- Demo result: added the optional Test role and the first-run session-mode recommendation.

Known platform behaviour that cannot be edited from the form: the live preview attaches an
auto-generated "example file" PDF to the demo session and says the skill writes it into the
workspace. The known-limitations text states that the skill writes no files.
