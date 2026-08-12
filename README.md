# Arcgentic

<p align="center">
  <img src="./assets/arcgentic-logo.png" alt="Arcgentic logo" width="168">
</p>

> **Arcgentic is a harness engineering layer for AI coding agents. It turns
> ad-hoc prompting into a gated engineering workflow.**

**中文文档 -> [README.zh-CN.md](./README.zh-CN.md)**

[![status](https://img.shields.io/badge/status-stable-brightgreen.svg)](#status)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v2.2.0-blueviolet.svg)](#status)
[![PyPI](https://img.shields.io/pypi/v/arcgentic.svg)](https://pypi.org/project/arcgentic/)
[![npm](https://img.shields.io/npm/v/arcgentic.svg)](https://www.npmjs.com/package/arcgentic)

Arcgentic helps Codex and Claude Code run software work as a disciplined
sequence: clarify the idea, plan the work, build it, self-audit it, optionally
run a realistic user test, audit it independently, then close only when the
evidence is good enough.

It is for people who already use AI coding tools, but do not want every session
to depend on memory, vibes, or a lucky prompt.

## Where it came from

Arcgentic started as the development discipline behind
[Moirai](https://github.com/Arch1eSUN/Moirai), a real agent project where AI
coding had to survive 30+ strict development rounds, repeated `NEEDS_FIX`
audits, planned handoffs, role boundaries, self-audit, external audit, and
recoverable session state.

This plugin packages the patterns that survived that work so Codex and Claude
Code users can apply them to their own complex projects. It is not a new coding
agent, and it does not copy Moirai-specific phase numbers, fact shapes, or
runtime internals. It is the workflow layer extracted from real agent
development.

## Harness engineering

Arcgentic sits in the harness layer around a coding agent.

Codex and Claude Code are the agents. Arcgentic is the engineering harness that
gives those agents roles, handoffs, stop states, audit gates, and evidence.
This is the same direction people describe as moving from vibe coding toward
agentic engineering: the important work is not only prompting the model, but
building the workflow around the model so its output can be checked, routed,
and trusted.

Related reading:

- [Martin Fowler / Thoughtworks: Harness engineering for coding agent users](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
- Andrej Karpathy's broader "vibe coding -> agentic engineering" framing

## 30-second version

| Question | Answer |
|---|---|
| What is it? | A harness engineering layer for Codex / Claude Code: roles, handoffs, audits, stop states, and pass/fix gates around the coding agent. |
| What problem does it solve? | AI coding sessions drift: scope changes silently, context gets lost, tests are skipped, and "done" often means "the assistant said it is done." |
| Who should use it? | Heavy Codex / Claude Code users, agent builders, AI-native teams, and people doing complex multi-round engineering work. |
| What does it add? | A repeatable gated workflow with automated role dispatch: planning, dev self-audit, optional user testing, external audit, and closeout. |
| What does it not do? | It does not replace your judgment, your tests, or your review process. It makes those steps harder to skip. |

## Platform status

| Platform | V2 status | Verification |
|---|---|---|
| **Codex** | Complete V2 | Verified in a real Codex project workflow, including automatic Orchestrator thread setup and role-thread dispatch. |
| **Claude Code** | Complete V2 | Verified in a real Claude Code session for `single-session-subagent` mode via a foreground `Agent` tier-0 broker dispatch — see `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`. That gate covered a single Planner role dispatch, not a full Planner→Developer→Auditor round loop. The `SendMessage`-based footer-correction retry path and `ListAgents` were not exercised by this gate (the footer was valid on the first attempt), and `multi-session-subthread` mode and the hook-backed fallback path remain unverified. |

Codex is the best current experience. In the verified Codex path, the current
project conversation becomes `Orchestrator`; Arcgentic then creates or reuses
the role threads, names them, sends the right role prompt, waits for their
return signal, and dispatches the next role without manual thread switching.

Claude Code support now has dogfood evidence for `single-session-subagent`
mode via a foreground `Agent` tier-0 broker dispatch, so treat that specific
path as a verified real workflow. The `SendMessage`-based footer-correction
retry path and `ListAgents` were not exercised by that gate, and
`multi-session-subthread` mode and the hook-backed fallback path have not yet
been verified in a real Claude Code session — all of these should still be
treated as unproven.

## Distribution status

| Channel | Status | Use it for |
|---|---|---|
| [GitHub Release](https://github.com/Arch1eSUN/Arcgentic/releases/tag/v2.2.0) | Published `v2.2.0` | Release notes, source archive, and verification context. |
| [PyPI](https://pypi.org/project/arcgentic/) | Published `arcgentic==2.2.0` | Python CLI: gates, V2 state helpers, Claude Code broker, and audit tooling. |
| [npm](https://www.npmjs.com/package/arcgentic) | Published `arcgentic@2.2.0` | Plugin asset bundle and Codex local install helper. |
| Claude Code plugin marketplace | Manifest ready | Main Claude Code install path; `single-session-subagent` mode now has dogfood evidence via a foreground `Agent` tier-0 broker dispatch, but `multi-session-subthread` mode and the hook-backed fallback path remain unverified. |

## Install

### Codex local install

```bash
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic
bash scripts/install-codex-local.sh --plugin-root .
```

Then start in a saved project workspace and ask:

```text
Use Arcgentic to build this idea: <your idea>
```

### npm bundle install

Use this if you want the Arcgentic plugin assets through npm:

```bash
npm install -g arcgentic
arcgentic install-codex-local
```

The npm package is a zero-dependency plugin bundle and Codex local install
helper. It includes the skills, agents, scripts, schemas, templates, and
platform manifests. The Python CLI is still published separately on PyPI.

### Claude Code install

```text
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

Then start inside your project:

```text
Use Arcgentic to build this idea: <your idea>
```

For Claude Code V2 experimental workflow setup:

If your Claude Code session's own tool list already includes `Agent`,
`SendMessage`, and `ListAgents` (native tooling / "tier 0"), no setup step
is needed — the session broker uses those tools directly and this is the
preferred, dogfood-verified path (see "Platform status" above). Only run
`install-hooks` below as a fallback, for sessions that lack those three
tools:

```bash
arcgentic claude-code-broker install-hooks \
  --settings .claude/settings.local.json \
  --state .agentic-rounds/state.yaml
```

### CLI install

Use this if you only need the command-line helper:

```bash
pipx install arcgentic
arcgentic --help
```

## Minimal example

Without Arcgentic:

```text
User: Build a small expense splitter.
AI: writes code
AI: says it is done
User: later discovers missing edge cases, unclear scope, no audit trail
```

With Arcgentic:

```text
User idea
-> current conversation becomes Orchestrator
-> Orchestrator creates or reuses Planner and sends the planning prompt
-> Planner returns the plan to Orchestrator
-> Orchestrator creates or reuses Developer and sends the dev prompt
-> Developer implements and returns a self-audit
-> Orchestrator dispatches optional Test only if realistic use needs it
-> Orchestrator creates or reuses Auditor and sends the audit prompt
-> Auditor returns PASS / NEEDS_FIX / AUDIT_INCOMPLETE
-> Orchestrator routes the next step
```

The important difference is not that the AI writes more text. The important
difference is that each role has a job, each stage has a stop condition, and
"done" is not accepted until the workflow can explain why.

## Arcgentic recommends a mode first

When you start Arcgentic with a new idea, the current session becomes
`Orchestrator`. Before it plans or builds, it should judge whether the idea is a
small fast project or a larger project that needs stronger review. Then it
recommends one project-level mode and asks you to confirm or override it:

| Mode | Choose it when | Tradeoff |
|---|---|---|
| **Single session, multiple agents** | You want the fastest run and a smaller demo surface. | Faster completion, weaker audit isolation. Planner, Developer, Test, and Auditor run inside the current Orchestrator session as fixed named role agents and are reused across rounds. |
| **Multiple sessions, multiple threads** | You want stronger separation between planning, development, testing, and audit. | Slower completion, stronger audit discipline. Planner, Developer, Test, and Auditor use fixed project threads. |

The choice is made once for the project. Arcgentic should not ask again every
round unless you start a new project or intentionally reset the workflow.

## What changes in real use

### Before

- One long AI coding session tries to remember everything.
- The assistant mixes planning, coding, review, and closeout in one context.
- Fixes are sometimes treated as audit work.
- The next session has to reconstruct what happened.
- "Pass" often means the assistant felt confident.

### After

- The current session is the Orchestrator.
- Planner, Developer, Test, and Auditor are separate roles.
- Developer owns building, repairs, and self-audit.
- Auditor owns stricter independent review.
- Test is used only when realistic user behavior needs separate verification.
- Closeout happens after the project/phase conditions are satisfied.

## The V2 workflow

Arcgentic V2 follows this shape:

```text
idea
-> brainstorm and planning
-> round handoff
-> development
-> developer self-audit
-> optional user-test
-> external audit
-> pass or fix
-> next round, next phase, or closeout
```

The roles are fixed:

| Role | Owns |
|---|---|
| **Orchestrator** | Routing, role dispatch, waiting, and deciding which role acts next. |
| **Planner** | Brainstorming, project plan, phase/round structure, handoffs, and closeout decisions. |
| **Developer** | Building, fixes, local verification, and self-audit. |
| **Test** | Realistic user/session testing when the plan says it is needed. |
| **Auditor** | Independent evidence review and PASS / NEEDS_FIX / AUDIT_INCOMPLETE decisions. |

Arcgentic does not create a new role identity every round. The role names stay
fixed: `Orchestrator`, `Planner`, `Developer`, `Test`, and `Auditor`.

## Custom role/state topology

The role/state routing that decides "who acts next" is no longer a hardcoded
table. It is a `Topology` (`toolkit/src/arcgentic/topology.py`) that a project
can override via `project.arcgentic_v2.topology` in `state.yaml` — routes,
which states each role may act from, and conditional next-role selection based
on the returning role's `artifacts` (for example, routing differently depending
on an audit outcome field). Zero-config projects get the exact same 5-role
sequence as before, byte for byte; custom topologies are validated at parse
time (unknown role keys and routes with no matching next state are rejected
before they can leave a project stuck mid-round). This is for projects that
need a different role graph than the default plan/dev/audit loop — most
projects should never need to touch it.

## Codex V2

Codex V2 is the verified path.

In Codex, Arcgentic can run either V2 mode.

The verified automation is:

```text
User starts in a project conversation
-> Arcgentic marks that conversation as Orchestrator
-> Orchestrator asks for or records the project mode
-> Orchestrator creates or reuses the fixed role thread/agent
-> Orchestrator sends the role-specific prompt and artifact pointers
-> the role finishes and actively returns to Orchestrator
-> Orchestrator consumes the return and dispatches the next role
```

The user should not have to manually create Planner, Developer, Test, or Auditor
threads in the verified Codex flow.

Single session, multiple agents:

```text
Current project thread = Orchestrator
-> Planner role agent
-> Developer role agent
-> optional Test role agent
-> Auditor role agent
-> Orchestrator continues
```

Multiple sessions, multiple threads:

```text
Current project thread = Orchestrator
-> create/reuse Planner thread and send Planner prompt
-> Planner returns to Orchestrator
-> create/reuse Developer thread and send Developer prompt
-> Developer returns to Orchestrator
-> create/reuse optional Test thread only when needed
-> create/reuse Auditor thread and send Auditor prompt
-> Auditor returns to Orchestrator
```

In multiple-thread mode, the Orchestrator should sleep after dispatching a
role. It wakes only when the role returns its result. That prevents the
Orchestrator from guessing when work is done or dispatching duplicate auditors.

In single-session mode, the Orchestrator stays in the same thread and runs the
named role agents directly. The role names still stay exact: Planner,
Developer, Test, and Auditor. Later rounds reuse those same role identities.

Use Codex V2 when you want the strongest current Arcgentic experience.

## Claude Code V2 experimental

Claude Code V2 is complete as an experimental version. `single-session-subagent`
mode now has real-session dogfood evidence via a foreground `Agent` tier-0
broker dispatch (see `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`);
`multi-session-subthread` mode and the hook-backed fallback path have not yet
been verified in a real Claude Code session.

The intended behavior is the same:

```text
current session = Orchestrator
-> create/reuse Planner session and send Planner prompt
-> Planner returns
-> create/reuse Developer session and send Developer prompt
-> Developer returns
-> optional Test only when needed
-> create/reuse Auditor session and send Auditor prompt
-> Auditor returns
```

Claude Code experimental mode aims to reach the same no-manual-routing behavior
through the session broker. That full automation has not yet been verified in a
real Claude Code session. If automatic return does not work in your setup, use
explicit copy-back: paste the role's return message into the Orchestrator so the
workflow can continue.

Use Claude Code V2 when you want to try the same discipline in Claude Code and
are comfortable with experimental workflow behavior.

## MCP-UI status panel

Arcgentic ships an optional MCP server exposing a live round-status panel via
[MCP Apps](https://modelcontextprotocol.io/specification/draft/extensions/apps)
(the January 2026 official MCP extension for rendering interactive UI inside a
conversation). Install it with:

```bash
pip install 'arcgentic[mcp]'
```

and declare it in your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "arcgentic": {
      "command": "arcgentic",
      "args": ["mcp-serve"]
    }
  }
}
```

Calling the `round_status_panel` tool renders round id, per-role dispatch
progress, and the latest audit verdict as an inline panel, with client-side
auto-refresh (capped, pauses when the panel isn't visible) and a "dispatch
next role" button that sends a chat message rather than mutating state
directly — the panel has no write path of its own; the Orchestrator still
drives every state change. On hosts without MCP Apps support (including plain
terminal Codex/Claude Code sessions), the same tool call falls back to a plain
text summary instead of failing.

MCP Apps host support is still young — this feature is for MCP-UI-capable
hosts (a graphical Claude/Codex client, not a bare terminal session).

## When to use Arcgentic

Use Arcgentic for:

- frequent Codex / Claude Code users who run real engineering work through AI;
- agent builders who need clear role boundaries and handoffs;
- small AI-native engineering teams;
- complex repos, multi-round development, refactors, and agent products;
- work where you need to prove AI-written code went through planning, testing,
  and audit before it was accepted;
- sessions where you want future you to understand what happened.

Arcgentic is intentionally heavier than normal prompting. If the task is not
substantial, risky, or multi-step, the workflow can feel like using a full
engineering gate for a tiny change.

Do not use Arcgentic for:

- a one-line command;
- a tiny copy edit;
- quick experiments where auditability does not matter;
- small tasks where normal Codex or Claude Code prompting is enough;
- exploratory questions with no development goal;
- work where you do not care about auditability.

## What a good Arcgentic run produces

A clean run should leave behind:

- a readable plan;
- a development result;
- a developer self-audit;
- a test report when the round needed realistic testing;
- an external audit verdict;
- a clear pass/fix/closeout decision.

These artifacts matter because they make the workflow inspectable. You can come
back later and see what was planned, what changed, what was checked, and why the
round was allowed to close.

## Demo and examples

Current evidence:

- Codex V2 has been exercised in a real project workflow.
- V2 completion evidence is recorded in the repository.
- Simulated user workflow evidence is recorded in the repository.

Planned adoption assets:

- short Codex demo;
- example project with before/after comparison;
- Claude Code experimental run notes for `multi-session-subthread` mode and
  the hook-backed fallback path, after those are verified in a real session
  (`single-session-subagent` mode's run notes already exist at
  `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`).

## Troubleshooting

### It starts creating too many sessions

Arcgentic V2 should reuse fixed role sessions. You should see only:

```text
Orchestrator
Planner
Developer
Test
Auditor
```

If you see `R1 Developer`, `R2 Auditor`, or similar names, that is not the
intended V2 behavior.

### The Orchestrator keeps acting after dispatch

The Orchestrator should stop after dispatching a role. It should resume only
when the role returns information. If it keeps dispatching while a role is still
working, the workflow is not following V2.

### Audit keeps looping

Audit should not loop forever. Auditor decides `PASS`, `NEEDS_FIX`, or
`AUDIT_INCOMPLETE`. If the evidence is missing and Developer can repair it, the
workflow should go back to Developer. If the same audit gap cannot be resolved
by another audit pass, it should stop instead of creating another auditor loop.

### Test runs every round

Test is optional. Planner decides whether the current round needs realistic
user/session testing. Many small rounds should go directly from
Developer self-audit to Auditor.

## Status

| Area | Status |
|---|---|
| Codex V2 | Complete and real-workflow verified. |
| Claude Code V2 | Complete experimental version; `single-session-subagent` mode has real-session dogfood evidence via a foreground `Agent` tier-0 broker dispatch, `multi-session-subthread` mode and the hook-backed fallback path are still pending. |
| Fixed roles | Complete. |
| Optional Test role | Complete. |
| Developer self-audit | Complete. |
| External audit | Complete. |
| Closed-project status no-op | Complete. |
| README onboarding | Updated for adoption-first use. |
| npm bundle | Published as `arcgentic@2.2.0`. |
| Custom role/state topology | Complete. Zero-config behavior unchanged; custom topologies validated at parse time. |
| MCP-UI status panel | Complete, optional (`pip install arcgentic[mcp]`). Depends on host MCP Apps support. |

## Roadmap

Near-term:

- verify Claude Code V2's `multi-session-subthread` mode, the
  `SendMessage`-based reuse-dispatch path, and the hook-backed fallback path
  in a real Claude Code session (`single-session-subagent` mode's
  first-dispatch/`create` path is verified; repeat dispatch via `SendMessage`
  is implemented but not yet dogfooded);
- publish a small example project;
- add a short demo walkthrough;
- collect issue-template feedback from first users.

Longer-term:

- harden V2 across more project types;
- improve example libraries for common workflows;
- keep the README focused on adoption and first-run clarity.

## Feedback

Open an issue if:

- install failed;
- the workflow was confusing;
- a role did the wrong job;
- your project did not fit the workflow;
- Claude Code experimental mode behaved differently from the docs.

Useful feedback includes:

- which platform you used: Codex or Claude Code;
- what you asked Arcgentic to build;
- where the workflow got stuck;
- whether the issue was planning, development, test, audit, or closeout.

## License

[MIT](./LICENSE) - Copyright (c) 2026 Arc Studio
