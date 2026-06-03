# Arcgentic

<p align="center">
  <img src="./assets/arcgentic-logo.png" alt="Arcgentic logo" width="168">
</p>

> **A**rc + **agentic** — agentic harness for rigorous round-driven development.

**中文文档 → [README.zh-CN.md](./README.zh-CN.md)**

[![status](https://img.shields.io/badge/status-stable-brightgreen.svg)](#status)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v1.0.0-blueviolet.svg)](#status)
[![PyPI](https://img.shields.io/pypi/v/arcgentic.svg)](https://pypi.org/project/arcgentic/)

`arcgentic` is a [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) / Codex-compatible plugin plus a Python CLI that turns four-role engineering discipline — *planning / development+self-audit / external-audit / reference-tracking* — into a **mechanically-enforced, state-machine-driven workflow**.

It works as:
- A **Python CLI** (`arcgentic`) for gates, audits, handoffs, and round utilities
- A **single-session orchestrator** that dispatches role sub-agents via the Claude Code Task tool
- A **project-level session mode** where a project chooses single-session orchestration
  or multi-session role isolation once, then stores that decision in `state.yaml`
- A **V1 source/spec layer** that records external workflow sources, marketplace capabilities,
  OpenSpec-style artifacts, and agency role families as auditable planning inputs

Either way, the state machine + gate scripts make discipline mechanical: if the gate fails, the state machine refuses to advance. No "remember to run audit-check" — the system runs it for you and blocks if it doesn't pass.

---

## Table of Contents

- [Why arcgentic](#why-arcgentic)
- [Quick install](#quick-install)
- [Quickstart — first round in 5 minutes](#quickstart--first-round-in-5-minutes)
- [How it works](#how-it-works)
- [The four roles](#the-four-roles)
- [State machine](#state-machine)
- [Single-session vs multi-session](#single-session-vs-multi-session)
- [Cost discipline](#cost-discipline)
- [Status & roadmap](#status--roadmap)
- [Origin](#origin)
- [Contributing](#contributing)
- [License](#license)

---

## Why arcgentic

Most LLM-assisted development workflows have rigorous *intent* but loose *enforcement*. "Remember to run audit-check." "Remember to scan references first." "Remember to update tech-debt." By the third round, the discipline erodes.

`arcgentic` makes the discipline **mechanical**:

| Layer | Mechanism |
|---|---|
| **State machine** | Every round transitions through enforced states (`intake → planning → dev → audit → passed / needs_fix → closed`). State stored in `.agentic-rounds/state.yaml`, validated against JSON Schema. |
| **Quality gates** | Every state transition has a Bash script. Plan must have N sections (or transition refuses). Dev commits must form an N-commit chain. Audit verdict must include a fact table where every fact is independently mechanically verifiable. |
| **Sub-agent dispatch** | Orchestrator dispatches role sub-agents via Claude Code's `Task` tool. Each sub-agent runs its own self-correction loop (TDD red-green / code review / contract verification) in isolated context, returning structured artifacts. |
| **Observation layer** | `lesson-codifier` sub-agent scans the last N rounds to detect patterns. 3 occurrences of same issue → propose new mandate. Novel preservation type → declare lesson streak iteration. |

---

## Quick install

### Prerequisites

- Bash 4+
- Python 3.13+ for the CLI toolkit
- Git
- Claude Code ≥ 1.0 (https://claude.com/claude-code)
- Codex, if you want local Codex plugin use
- Optional but recommended: `superpowers` plugin + `plugin-dev` plugin

```bash
# verify
bash --version       # >= 4
python3 --version    # >= 3.13 for the Python package
```

### Method 1 — Python CLI from PyPI

Use this when you want the `arcgentic` command without cloning the repo:

```bash
pipx install arcgentic

# or
uv tool install arcgentic

arcgentic --help
arcgentic audit-check --help
```

PyPI package: https://pypi.org/project/arcgentic/

### Method 2 — Claude Code marketplace

```
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

This installs the Claude Code plugin from the marketplace manifest at
`.claude-plugin/marketplace.json`.

### Method 3 — Manual Claude Code install

```bash
# Clone into Claude Code's user-level skills directory
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone git@github.com:Arch1eSUN/Arcgentic.git arcgentic

# Or via HTTPS:
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic

# Verify
ls ~/.claude/skills/arcgentic/.claude-plugin/plugin.json
claude plugin validate ~/.claude/skills/arcgentic
```

Now in any Claude Code session, you can invoke arcgentic skills:
- `arcgentic:using-arcgentic`
- `arcgentic:audit-round`
- `arcgentic:orchestrate-round`
- ...

### Method 4 — Codex local plugin

`arcgentic` also ships a Codex plugin manifest at `.codex-plugin/plugin.json`.
For local Codex use, copy or clone the repo under your personal plugin folder:

```bash
mkdir -p ~/plugins
cd ~/plugins
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic
git checkout v1.0.0

# Validate Codex plugin manifest
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ~/plugins/arcgentic
```

If you manage Codex plugins through a personal marketplace, add this entry to
`~/.agents/plugins/marketplace.json`:

```json
{
  "name": "arcgentic",
  "source": {
    "source": "local",
    "path": "./plugins/arcgentic"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

### Method 5 — OpenClaw git-source bundle

`arcgentic` ships `openclaw.plugin.json` so OpenClaw can detect it as a bundle plugin.

```bash
openclaw plugins install git:github.com/Arch1eSUN/Arcgentic@main
openclaw plugins inspect arcgentic
```

### Method 6 — Source install for toolkit development

```bash
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic/toolkit
python3 -m pip install -e ".[dev]"
arcgentic --help
```

V1 local source/spec commands:

```bash
arcgentic session-mode recommend --round R1 --handoff docs/superpowers/plans/R1.md
arcgentic session-mode prompt --round R1 --handoff docs/superpowers/plans/R1.md --mode multi-session --role developer
arcgentic orchestrator-dispatch --round R1 --handoff docs/superpowers/plans/R1.md --mode multi-session
arcgentic source-intake validate docs/source-intake/*.yaml
arcgentic capability-registry build .claude-plugin/marketplace.json
arcgentic spec-governance status openspec/changes/<change>
arcgentic agency-roster inspect references/agency-agents
arcgentic verdict-completeness docs/audits/R1.md
arcgentic close-round --state-file .agentic-rounds/state.yaml --verdict docs/audits/R1.md --audit-commit <sha>
arcgentic v1-release-readiness --repo-root .
```

---

## Quickstart — first round in 5 minutes

### 1. Initialize state machine in your project

```bash
cd ~/projects/your-project

bash ~/.claude/skills/arcgentic/scripts/state/init.sh \
  --project-root . \
  --project-name "your-project" \
  --round-naming "phase.round[.fix]"
```

This creates `.agentic-rounds/state.yaml` in `intake` state. The file is the single source of truth for every role from now on.

> Tip: `.agentic-rounds/` is gitignored by default. Projects opt in to committing it.

### 2. Start a Claude Code session in the project

```bash
cd ~/projects/your-project
claude
```

In the chat, ask Claude to read the state and tell you what to do next:

```
Read .agentic-rounds/state.yaml and run pickup.sh to tell me what role I should take and what I should do.
```

Claude will load `arcgentic:using-arcgentic`, run `pickup.sh`, and reply with something like:

> *Current state: `intake`. Role: founder. Action: State the round scope (name, goal, in-scope/out-of-scope). Next state: `planning`.*

### 3. State your round scope

You write the scope. Claude (in planner role) writes the handoff document. State machine advances.

### 4. Run dev / audit / close

The orchestrator skill (`arcgentic:orchestrate-round`) walks you through every state, dispatches the planner / developer / auditor / reference-tracker sub-agents where appropriate, and runs every gate before transitions.

When the round reaches `closed`, you've completed one full disciplined cycle.

### Full walkthrough

See `docs/plans/2026-05-12-arcgentic-mvp-plan.md` for the full implementation plan + the "live run" dogfood gate in `tests/dogfood/gate-2-live-run/` for a worked example.

---

## How it works

```
arcgentic/
├── plugin.json                # plugin manifest
├── schema/state.schema.json   # JSON Schema for .agentic-rounds/state.yaml
├── skills/                    # Layer 1: per-role discipline (Markdown SKILL.md)
│   ├── using-arcgentic/       #   entry skill
│   ├── pre-round-scan/        #   shared prelude — every role's first action
│   ├── orchestrate-round/     #   orchestrator role
│   ├── audit-round/           #   external auditor role
│   ├── close-round/           #   PASS-only closeout seam
│   ├── verify-gates/          #   manual gate runner
│   ├── plan-round/            #   planner role
│   ├── execute-round/         #   developer + self-audit role
│   ├── track-refs/            #   reference tracker role
│   ├── codify-lesson/         #   lesson codification role
│   └── cross-session-handoff/ #   multi-session handoff role
├── agents/                    # Layer 2: platform-neutral sub-agent definitions
│   ├── orchestrator.md        #   top-level round driver
│   ├── auditor.md             #   Task-tool-dispatched external auditor
│   ├── planner.md             #   planning sub-agent
│   ├── developer.md           #   development sub-agent
│   ├── ba-designer.md         #   design review sub-agent
│   ├── cr-reviewer.md         #   code review sub-agent
│   ├── se-contract.md         #   contract verification sub-agent
│   ├── lesson-codifier.md     #   lesson pattern sub-agent
│   └── ref-tracker.md         #   reference tracker sub-agent
├── scripts/                   # Layer 3: state-machine + gate enforcement (Bash)
│   ├── state/                 #   init / transition / pickup / validate-schema
│   ├── gates/                 #   handoff-doc / round-commit-chain / verdict-fact-table
│   └── lib/                   #   yaml.sh, state.sh helpers
└── hooks/examples/            # Layer 4: optional commit-level enforcement (project opt-in)
```

Four layers, top to bottom: skills tell Claude *how to think* in a given role; agents let the orchestrator *delegate* a role to a sub-agent; scripts *enforce* the state machine; hooks *defend* at commit time.

---

## The four roles

| Role | Responsibilities | Current skill | Current agent |
|------|------------------|--------------------|--------------------|
| **Planner** | Read scope → write 16-section handoff doc → advance state to `awaiting_dev_start` | ✅ `plan-round` | ✅ `planner` |
| **Developer** | Read handoff → execute task-by-task with inline self-finalization (BA + CR + SE) → produce N-commit chain | ✅ `execute-round` | ✅ `developer` |
| **External auditor** | Read handoff + commit chain → write verdict with mechanically-verifiable fact table → apply lesson codification protocol → advance to `passed` or `needs_fix` | ✅ `audit-round` | ✅ `auditor` |
| **Reference tracker** | Daily git fetch over `references/` → categorize new clones → maintain `INDEX.md` | ✅ `track-refs` | ✅ `ref-tracker` |

Plus a meta-role:
- **Orchestrator** — drives the state machine end-to-end, dispatches sub-agents when role-switching is needed, and owns PASS-only closeout through the `close-round` seam. ✅ `orchestrate-round` skill + `orchestrator` agent.

---

## State machine

```
       ┌─────────┐
       │ intake  │
       └────┬────┘
            │ founder states scope
            ▼
       ┌──────────┐
       │ planning │
       └─────┬────┘
             │ planner writes handoff
             │ [GATE: handoff-doc-gate.sh]
             ▼
   ┌────────────────────┐
   │ awaiting_dev_start │
   └──────────┬─────────┘
              │
              ▼
   ┌────────────────────┐
   │  dev_in_progress   │ ←──────┐
   └──────────┬─────────┘        │
              │ [GATE: round-commit-chain-gate.sh]
              ▼                  │
   ┌────────────────────┐        │
   │  awaiting_audit    │        │
   └──────────┬─────────┘        │
              │                  │
              ▼                  │
   ┌────────────────────┐        │
   │ audit_in_progress  │        │
   └──────────┬─────────┘        │
              │ [GATE: verdict-fact-table-gate.sh]
        ┌─────┴─────┐            │
        ▼           ▼            │
   ┌────────┐  ┌──────────┐      │
   │ passed │  │needs_fix │      │
   └───┬────┘  └─────┬────┘      │
       │             │           │
       ▼             ▼           │
   ┌────────┐  ┌─────────────┐   │
   │ closed │  │fix_in_progress│ ┘ (→ awaiting_audit again)
   └────────┘  └─────────────┘
```

Every transition is run by `scripts/state/transition.sh`:
1. Verifies the target state is in the current state's `next` list
2. Runs the required gate script (refuses transition if gate fails)
3. Updates `current_round.state` + appends to `state_history`

Try to skip a state? Refused. Try to PASS with an unverified fact table? Refused. Try to close a round before PASS audit + strict audit-check? Refused. The state machine is the enforcement.

---

## Single-session vs multi-session

### Mode A — Single-session (orchestrator drives all)

ONE Claude session. Loads `arcgentic:orchestrate-round`. Dispatches role sub-agents via Task tool when role-switching is needed.

**Use when**: solo developer / small project / proof-of-concept.

### Mode B — Multi-session (each human runs a role)

MULTIPLE Claude sessions, each loaded with a different role skill:
- Session 1 (founder + planner) — `arcgentic:plan-round`
- Session 2 (developer) — `arcgentic:execute-round`
- Session 3 (auditor) — `arcgentic:audit-round`
- Session 4 (ref-tracker) — `arcgentic:track-refs`

`state.yaml` is the inter-session protocol. Every session reads it on entry.

**Use when**: team of humans / long-lived projects / strict audit independence required.

Both modes share the same `state.yaml` schema and gate scripts. The mode is a
project-level decision stored at `project.session_mode`; once set, future rounds
do not ask again unless the project is explicitly reconfigured.

---

## Cost discipline

`arcgentic` is **strictly cost-disciplined**:

- ❌ No paid-API calls (OpenAI / Anthropic API / Gemini / etc.) anywhere in plugin code
- ❌ No background processes / daemons / cron triggers
- ❌ No auto-pull from cloud LLMs as part of "normal flow"
- ✅ All LLM reasoning happens in your Claude Code subscription
- ✅ References pulled via manual `git fetch` only (no auto-cron)

If a sub-agent dispatched via Task tool tries to break any of these, the orchestrator refuses + reports.

This is non-negotiable, derived from the original Moirai project's `§ 4 cost-discipline` mandate.

---

## Status & roadmap

### Current — `v1.0.0`

- ✅ Plugin scaffold + JSON Schema (`schema/state.schema.json`)
- ✅ Foundation: 4 state scripts + 3 gate scripts + lib helpers + tests (9 test files / 48 bash assertions, 100% passing per TDD discipline) — from v0.1.0
- ✅ Python toolkit at `toolkit/` (Path C hybrid monorepo):
  - 6 IDE adapter implementations (ClaudeCode canonical + Cursor + VSCode-Codex + Codex CLI + Inline fallback) + `detect_adapter()` auto-detection
  - audit_check engine with AC-1 + AC-3 mechanical fact-verification
  - 4 quality gates aggregator (`quality-gate-enforce`)
  - 323 pytest unit + property + integration tests; mypy --strict clean; ruff clean
- ✅ 11 markdown skills (v0.1.0 foundation + plan-round + execute-round + close-round + codify-lesson + track-refs + cross-session-handoff)
- ✅ 9 markdown agents (orchestrator/auditor + planner/developer/BA/CR/SE + lesson-codifier + ref-tracker)
- ✅ Hooks: pre-commit-fact-check, quality-gate-enforce, round-boundary-lesson-scan
- ✅ 3 handoff templates + 3 finalization templates (18/12/10-section handoff + BA design + self-audit + external verdict)
- ✅ P1 complete: `codify-lesson`, `track-refs`, `round-boundary-lesson-scan`, RT classifier, pattern detection
- ✅ P2 complete: `cross-session-handoff` with TTL lock + atomic state writes + history snapshots
- ✅ execute-round self-audit now runs audit-check instead of reporting ER-AUDIT-GATE-4 skipped
- ✅ V1 release hardening: project-level session mode, orchestrator dispatch
  order output, role-specific identity prompts, structured verdict completeness,
  and strict-audit-check-backed `close-round` seam
- ✅ Python CLI version aligned for PyPI release as `arcgentic==1.0.0`
- ✅ GitHub Actions trusted publishing workflow for PyPI releases
- ✅ Claude Code plugin manifest + marketplace at `.claude-plugin/`
- ✅ Codex local plugin manifest at `.codex-plugin/plugin.json`
- ✅ OpenClaw git-source bundle manifest at `openclaw.plugin.json`
- ✅ Dogfood Gate 1 (structural-fidelity replay against Moirai R10-L3-llm verdict — PASS, from v0.1.0)
- ✅ Dogfood Gate 2 (v0.1.0-alpha.2-meta round closed PASS — from v0.1.0)
- ✅ V1 dogfood R1: source-intake / capability-registry / spec-governance / agency-roster round closed PASS
- ✅ V1 dogfood R2: project-level session mode / dispatch / close-round release-hardening round closed PASS
- ✅ V1 dogfood R3: prepublish self-audit stability + codify-lesson precision fix round closed PASS

### Next — `v1.0.x` / `v1.1.0`

- Cross-project portability hardening on 2-3 non-Moirai repositories
- Rich execute-round fact generation from commit chain and changed files
- ER-RETRY: retry-with-context loops for sub-agent dispatches
- GitHub reference discovery/search feeding `track-refs`

### `v1.0.0` stable

Stable release cut after R1-R3 live dogfood and external audit. Follow-up work should stay
in `v1.0.x` / `v1.1.0` unless it is a release-blocking regression.

---

## Origin

`arcgentic` distills patterns from **30+ rigorous development rounds** on the [Moirai](https://github.com/Arch1eSUN/Moirai) project — a local-first cognitive substrate where the founder paid premium for engineering discipline:

- Manus-grade typed errors at runtime boundaries
- Hypothesis property tests for every claimed invariant
- Protocol-parity testing across multiple impls
- `doc-vs-impl` re-grep mandate (re-read impl source before claiming spec)
- Reference-first development order (6 steps: references/ → fuse → adapt → lang-fit → external → from-scratch)
- 4-column reference triplet (which / why / what-part / NOT used)
- RT0–RT3 reference tier taxonomy (inspiration / source adapt / binary vendor / full dep)
- Lesson codification protocol (observe 3× → infer → verify → encode → declare NOVEL preservation type)

The patterns that **survived the most NEEDS_FIX iterations** are what made it into this plugin.

What's in arcgentic: the **patterns**.
What's NOT in arcgentic: the **specific instances** (Moirai's Phase numbers, fact-shape #1–16+, EventLog 8-invariants, V2 envelope schema, ...).

---

## Contributing

This is `v1.0.0`. If you have:
- **Bug reports** — open an issue with a reproducer
- **Portability bugs** — open an issue tagged `portability` with the project type / OS / Claude Code version
- **Feature suggestions** — open a discussion (we'll evaluate against the [forward plan](#status--roadmap))
- **Pull requests** — please open an issue first to discuss; PRs without prior discussion may be deferred to the next minor release

---

## License

[MIT](./LICENSE) — Copyright (c) 2026 Arc Studio
