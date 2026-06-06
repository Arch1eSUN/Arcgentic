# Arcgentic

<p align="center">
  <img src="./assets/arcgentic-logo.png" alt="Arcgentic logo" width="168">
</p>

> **Arcgentic turns AI coding from ad-hoc prompting into a gated engineering workflow.**

**中文文档 -> [README.zh-CN.md](./README.zh-CN.md)**

[![status](https://img.shields.io/badge/status-stable-brightgreen.svg)](#status)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v1.0.0-blueviolet.svg)](#status)
[![PyPI](https://img.shields.io/pypi/v/arcgentic.svg)](https://pypi.org/project/arcgentic/)

Arcgentic helps Codex and Claude Code run software work as a disciplined
sequence: clarify the idea, plan the work, build it, self-audit it, optionally
run a realistic user test, audit it independently, then close only when the
evidence is good enough.

It is for people who already use AI coding tools, but do not want every session
to depend on memory, vibes, or a lucky prompt.

## Where it came from

Arcgentic started as the development discipline behind
[Moirai](https://github.com/Arch1eSUN/Moirai), a real agent project where AI
coding needed planned rounds, role boundaries, self-audit, external audit, and
recoverable handoffs.

This plugin packages that discipline so Codex and Claude Code users can apply it
to their own complex projects. It is not a new coding agent. It is the workflow
layer extracted from real agent development.

## 30-second version

| Question | Answer |
|---|---|
| What problem does it solve? | AI coding sessions drift: scope changes silently, context gets lost, tests are skipped, and "done" often means "the assistant said it is done." |
| Who should use it? | Heavy Codex / Claude Code users, agent builders, AI-native teams, and people doing complex multi-round engineering work. |
| What does it add? | A repeatable gated workflow with planning, dev self-audit, optional user testing, external audit, and closeout. |
| What does it not do? | It does not replace your judgment, your tests, or your review process. It makes those steps harder to skip. |

## Platform status

| Platform | V2 status | Verification |
|---|---|---|
| **Codex** | Complete V2 | Verified in a real Codex project workflow. |
| **Claude Code** | Complete V2 experimental | Not yet verified in a real Claude Code session. |

Codex is the best current experience. Claude Code support is available as an
experimental version and should be treated as a real workflow candidate, not as
proven production behavior yet.

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
-> Planner creates the project plan and first round
-> Developer implements and writes a self-audit
-> Test runs only if this round needs realistic user/session testing
-> Auditor independently checks evidence
-> Planner closes the phase or starts the next round
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

## Codex V2

Codex V2 is the verified path.

In Codex, Arcgentic can run either V2 mode.

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
-> Planner thread
-> Developer thread
-> optional Test thread
-> Auditor thread
-> back to Orchestrator
```

In multiple-thread mode, the Orchestrator should sleep after dispatching a
role. It wakes only when the role returns its result. That prevents the
Orchestrator from guessing when work is done or dispatching duplicate auditors.

In single-session mode, the Orchestrator stays in the same thread and runs the
named role agents directly. The role names still stay exact: Planner,
Developer, Test, and Auditor. Later rounds reuse those same role identities.

Use Codex V2 when you want the strongest current Arcgentic experience.

## Claude Code V2 experimental

Claude Code V2 is complete as an experimental version, but it has not yet been
verified in a real Claude Code session.

The intended behavior is the same:

```text
Orchestrator
-> Planner
-> Developer
-> optional Test
-> Auditor
-> Orchestrator
```

Claude Code experimental mode aims to keep the same role flow. If automatic
return does not work in your setup, use explicit copy-back: paste the role's
return message into the Orchestrator so the workflow can continue.

Use Claude Code V2 when you want to try the same discipline in Claude Code and
are comfortable with experimental workflow behavior.

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
- Claude Code experimental run notes after real-session verification.

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
| Claude Code V2 | Complete experimental version; real-session verification pending. |
| Fixed roles | Complete. |
| Optional Test role | Complete. |
| Developer self-audit | Complete. |
| External audit | Complete. |
| Closed-project status no-op | Complete. |
| README onboarding | Updated for adoption-first use. |

## Roadmap

Near-term:

- verify Claude Code V2 in a real Claude Code session;
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
