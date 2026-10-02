---
name: arcgentic
description: Use when the user mentions Arcgentic, or wants substantial AI-written code taken through a gated plan → development → self-audit → external audit workflow with role handoffs and evidence before it counts as done. Explains what Arcgentic is, when it fits, and how to install the full plugin for Codex or Claude Code.
license: MIT
---

# Arcgentic

Arcgentic is a harness-engineering layer for Codex and Claude Code. It wraps the
coding agent in roles, handoffs, audits, stop states, and pass/fix gates, so a
round of work only closes when there is evidence: a plan, a developer
self-audit, optional user testing, and an independent external audit.

This skill is the **entry point** listed on Agensi. The workflow itself lives in
the open-source Arcgentic plugin (MIT), which ships its own skills, agents,
hooks, and a Python CLI. This skill does not contain that code. It tells you
when Arcgentic fits and how to install the real thing.

- Source of truth: https://github.com/Arch1eSUN/Arcgentic
- PyPI: https://pypi.org/project/arcgentic/
- npm: https://www.npmjs.com/package/arcgentic

## When to use it

Good fit:

- real engineering work run through Codex or Claude Code, across multiple rounds;
- complex repos, refactors, and agent products;
- work where you must show that AI-written code was planned, tested, and audited
  before it was accepted;
- sessions where a future reader needs to understand what happened and why.

Not a good fit: one-line commands, tiny edits, quick experiments, or exploratory
questions with no development goal. Arcgentic is intentionally heavier than
normal prompting.

## What to do when this skill triggers

1. Check whether the Arcgentic plugin is already installed in this agent. In
   Claude Code, look for the `arcgentic` plugin and its skills such as
   `using-arcgentic`. In Codex, look for the `arcgentic` skill from the plugin.
2. If it is installed, hand off to the plugin's own entry skill and follow it.
   Do not improvise the workflow from this summary.
3. If it is not installed, explain what Arcgentic does, show the install steps
   below for the user's agent, and let the user run them. Do not install
   anything without the user's go-ahead.

## Install

### Claude Code

```text
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

Then, inside your project:

```text
Use Arcgentic to build this idea: <your idea>
```

### Codex

```bash
npm install -g arcgentic
arcgentic install-codex-local
```

Then start in a saved project workspace and ask:

```text
Use Arcgentic to build this idea: <your idea>
```

### Command-line helper only

```bash
pipx install arcgentic
arcgentic --help
```

### Optional MCP status panel

Arcgentic also ships an optional MCP server that renders the current round's
status, role dispatch progress, and audit verdict as an inline panel:

```bash
claude mcp add --transport stdio arcgentic -- uvx --python 3.13 --from 'arcgentic[mcp]' arcgentic mcp-serve
```

Requires Python 3.13 or newer.

## Supported agents

Arcgentic's full workflow is built for **Codex** and **Claude Code**. In other
agents, this skill can still explain Arcgentic and the command-line helper works
anywhere Python 3.13 is available, but the role dispatch and session
orchestration are not supported there.

## How a round works

1. **Planner** turns the idea into a scoped handoff.
2. **Developer** implements it and writes a self-audit.
3. **Test** (optional) runs a realistic user test.
4. **Auditor** reviews independently and returns PASS or a fix list.
5. The round closes only on PASS with evidence; otherwise it loops back.

Arcgentic recommends a session mode before the first round: a faster
single-session mode with named subagents, or a slower multi-session mode with
fixed role threads and stronger audit isolation.

## License

MIT. See `LICENSE` in this package and in the GitHub repository.
