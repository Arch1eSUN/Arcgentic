# Arcgentic

> **A**rc + **agentic** — agentic harness for rigorous round-driven development.

**中文文档 → [README.zh-CN.md](./README.zh-CN.md)**

[![status](https://img.shields.io/badge/status-alpha-orange.svg)](#status)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v0.1.0--alpha-blueviolet.svg)](#status)

`arcgentic` is a [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) plugin that turns four-role engineering discipline — *planning / development+self-audit / external-audit / reference-tracking* — into a **mechanically-enforced, state-machine-driven workflow**.

It works as:
- A **single-session orchestrator** that dispatches role sub-agents via the Claude Code Task tool, OR
- A **multi-session toolkit** where each Claude session loads one role's skill while a shared `state.yaml` is the inter-session protocol.

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
- Python 3.8+
- Git
- Claude Code ≥ 1.0 (https://claude.com/claude-code)
- Optional but recommended: `superpowers` plugin + `plugin-dev` plugin

```bash
# verify
bash --version       # >= 4
python3 --version    # >= 3.8
python3 -c "import yaml, jsonschema; print('ok')"
```

If the last command fails:
```bash
python3 -m pip install --user PyYAML jsonschema
```

### Method 1 — Claude Code marketplace (when v0.1.0 stable lands)

```
/plugin install Arch1eSUN/Arcgentic
```

> *Not available yet — the plugin is currently `v0.1.0-alpha`. Use Method 2 for now.*

### Method 2 — Manual install (alpha + dev)

```bash
# Clone into Claude Code's user-level plugins directory
mkdir -p ~/.claude/plugins
cd ~/.claude/plugins
git clone git@github.com:Arch1eSUN/Arcgentic.git arcgentic

# Or via HTTPS:
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic

# Verify
ls ~/.claude/plugins/arcgentic/plugin.json
```

Now in any Claude Code session, you can invoke arcgentic skills:
- `arcgentic:using-arcgentic`
- `arcgentic:audit-round`
- `arcgentic:orchestrate-round`
- ...

---

## Quickstart — first round in 5 minutes

### 1. Initialize state machine in your project

```bash
cd ~/projects/your-project

bash ~/.claude/plugins/arcgentic/scripts/state/init.sh \
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

The orchestrator skill (`arcgentic:orchestrate-round`) walks you through every state, dispatches sub-agents where supported (auditor in MVP, more in v0.2+), and runs every gate before transitions.

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
│   ├── verify-gates/          #   manual gate runner
│   └── (post-MVP) plan-round, execute-round, track-refs, codify-lesson, ...
├── agents/                    # Layer 2: platform-neutral sub-agent definitions
│   ├── orchestrator.md        #   top-level round driver
│   ├── auditor.md             #   Task-tool-dispatched external auditor
│   └── (post-MVP) planner, developer, ref-tracker, lesson-codifier, ...
├── scripts/                   # Layer 3: state-machine + gate enforcement (Bash)
│   ├── state/                 #   init / transition / pickup / validate-schema
│   ├── gates/                 #   handoff-doc / round-commit-chain / verdict-fact-table
│   └── lib/                   #   yaml.sh, state.sh helpers
└── hooks/examples/            # Layer 4: optional commit-level enforcement (project opt-in)
```

Four layers, top to bottom: skills tell Claude *how to think* in a given role; agents let the orchestrator *delegate* a role to a sub-agent; scripts *enforce* the state machine; hooks *defend* at commit time.

---

## The four roles

| Role | Responsibilities | MVP-supported skill | MVP-supported agent |
|------|------------------|--------------------|--------------------|
| **Planner** | Read scope → write 16-section handoff doc → advance state to `awaiting_dev_start` | ⏳ (post-MVP `plan-round`) | ⏳ |
| **Developer** | Read handoff → execute task-by-task with inline self-finalization (BA + CR + SE) → produce N-commit chain | ⏳ (post-MVP `execute-round`) | ⏳ |
| **External auditor** | Read handoff + commit chain → write verdict with mechanically-verifiable fact table → apply lesson codification protocol → advance to `passed` or `needs_fix` | ✅ `audit-round` | ✅ `auditor` |
| **Reference tracker** | Daily git fetch over `references/` → categorize new clones → maintain `INDEX.md` | ⏳ (post-MVP `track-refs`) | ⏳ |

Plus a meta-role:
- **Orchestrator** — drives the state machine end-to-end, dispatches sub-agents when role-switching is needed. ✅ `orchestrate-round` skill + `orchestrator` agent.

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

Try to skip a state? Refused. Try to PASS with an unverified fact table? Refused. Try to close a round before audit? Refused. The state machine is the enforcement.

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

Both modes share the same `state.yaml` schema and gate scripts. You can switch mid-round.

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

### Current — `v0.1.0-alpha`

- ✅ Plugin scaffold + JSON Schema (`schema/state.schema.json`)
- ✅ Foundation: 4 state scripts + 3 gate scripts + lib helpers + tests (100% passing per TDD discipline)
- ✅ 5 skills: `using-arcgentic`, `pre-round-scan`, `verify-gates`, `audit-round`, `orchestrate-round`
- ✅ 2 sub-agents: `orchestrator`, `auditor`
- ⏳ Dogfood Gate 1 (replay validation)
- ⏳ Dogfood Gate 2 (live run on arcgentic-on-arcgentic)
- ⏳ Dogfood Gate 3 (cross-project portability) — deferred to pre-stable

### Next — `v0.2.0`

Full role coverage:
- `plan-round` skill + `planner` sub-agent
- `execute-round` skill + `developer` sub-agent
- `track-refs` skill + `ref-tracker` sub-agent
- `codify-lesson` skill + `lesson-codifier` sub-agent
- `cross-session-handoff` skill

### Later — `v0.3.0`

Hooks layer:
- `pre-commit-round-id-required.sh`
- `post-commit-update-state.sh`
- `pre-push-gate-verification.sh`

### `v1.0.0` stable

After Gate 3 passes on 2-3 non-Moirai projects: promote to stable + submit to Claude Code plugin marketplace.

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

This is `v0.1.0-alpha`. The plugin is being battle-tested before opening contributions. If you have:
- **Bug reports** — open an issue with a reproducer
- **Portability bugs** — open an issue tagged `portability` with the project type / OS / Claude Code version
- **Feature suggestions** — open a discussion (we'll evaluate against the [forward plan](#status--roadmap))
- **Pull requests** — please open an issue first to discuss; PRs without prior discussion may be deferred until v1.0.0

---

## License

[MIT](./LICENSE) — Copyright (c) 2026 Arc Studio
