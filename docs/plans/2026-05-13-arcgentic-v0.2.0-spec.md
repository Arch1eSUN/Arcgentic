# arcgentic v0.2.0 — Complete Implementation Specification

> **Source**: Arc Studio Moirai-derived harness engineering discipline, distilled for arcgentic v0.2.0
> **Target IDEs/Agents**: VSCode + Codex / Cursor / Claude Code / Codex CLI (single source-of-truth spec; platform adapters in § 3)
> **Authored**: 2026-05-20 by Claude Opus 4.7 (Moirai-side) for arcgentic dev session
> **Reading order**: § 0 → § 2 (vocabulary) → § 3 (IDE adapter) → § 4 (skills) → § 5 (agents) → § 6 (hooks) → § 7-§ 14 (templates) → § 19 (impl order) → § 20 (acceptance)
> **Total scope**: 5 NEW skills + 7 NEW agents + 3 NEW hooks; ~30-33h projected (~15-20h actual at MVP-velocity)
> **Self-contained**: dev session does NOT need to fetch Moirai-repo content; everything is inlined below

---

## § 0. Document scope + read order

### 0.1 What this document IS

A complete, self-contained spec for arcgentic v0.2.0. Reading this document end-to-end gives the dev session everything needed to ship v0.2.0:
- All skill algorithms + agent contracts + hook triggers
- Full templates (handoff / BA design / self-audit / external audit verdict)
- Mandate vocabulary, RT tier classification, Lesson 8 protocol, fact-table format
- IDE adapter layer for VSCode/Cursor/Codex/Claude Code unification
- File structure, implementation order, acceptance criteria

### 0.2 What this document is NOT

- NOT Moirai source code (arcgentic and Moirai are separate products with compatible discipline)
- NOT a copy of Moirai's `.claude/skills/` directory (those are for Moirai's specific workflows)
- NOT prescriptive about runtime LLM choice — arcgentic is platform-agnostic; the harness wraps whatever AI is hosting it

### 0.3 v0.2.0 delivery scope

| Category | v0.1.0-alpha.2 had | v0.2.0 adds | v0.2.0 total |
|---|---:|---:|---:|
| Skills | 5 | 5 | 10 |
| Agents | 2 | 7 | 9 |
| Hooks | 0 | 3 | 3 |

**5 NEW skills**: `plan-round` (P0) / `execute-round` (P0) / `codify-lesson` (P1) / `track-refs` (P1) / `cross-session-handoff` (P2)

**7 NEW agents**: `planner` (P0) / `developer` (P0) / `ba-designer` (P0) / `cr-reviewer` (P0) / `se-contract` (P0) / `lesson-codifier` (P1) / `ref-tracker` (P1)

**3 NEW hooks**: `pre-commit-fact-check` / `round-boundary-lesson-scan` / `quality-gate-enforce`

### 0.4 P0 / P1 / P2 priority groups

- **P0 (must-have for v0.2)**: plan-round + execute-round + 5 agents (planner / developer / ba-designer / cr-reviewer / se-contract) + pre-commit-fact-check hook + quality-gate-enforce hook. **18-21h**.
- **P1 (high-value follow-on)**: codify-lesson + track-refs + 2 agents (lesson-codifier / ref-tracker) + round-boundary-lesson-scan hook. **9h**.
- **P2 (nice-to-have, mode-B)**: cross-session-handoff. **3h**.

Recommended split: v0.2.0 = P0 only; v0.2.1 = P1 add; v0.2.2 = P2 add.

---

## § 1. Foundational principles inherited from Moirai

These are the WHY behind everything in v0.2.0. Internalize before reading § 2 vocabulary.

### 1.1 Round-based development with 4-commit chain

Every meaningful unit of work is a **round** (`R{N}.{M}` or `R{phase}-{name}`). Each round produces exactly **4 commits**: entry-admin → BA design → dev body → state refresh + self-audit. This rhythm is load-bearing: it enforces design-before-code (BA pass), test-first-before-claim (dev body 4-gate), and audit-after-ship (self-audit) — all without process being optional.

### 1.2 Inline-self-finalization (Option A — mandate #17(d) clause (h))

A single round's dev session executes BA design + CR review + SE contract review **inline within the same session**, not as separate roundtrips with external reviewers. The reviewer is an **agency-agent** dispatched as a sub-process; its output lands in self-audit handoff § 2.2 / § 2.3. Three-way reconciliation (BA + CR + SE) happens in one go.

**Why inline**: external roundtrips lose context + add days. Inline preserves context but requires the dev session to discipline itself with a verifying skill (verification-before-completion equivalent).

### 1.3 SE CONTRACT-ONLY isolation (mandate #20)

Security Engineer briefs are given **threat surfaces DIRECT, NOT BA-derived**. SE reads the contract / spec / API surface; SE does NOT read BA's design doc. This isolation is load-bearing: if SE reads BA design, SE recapitulates known issues; if SE reads only the contract, SE finds NOVEL P3 findings.

**Operational rule**: the se-contract agent's input must be `<contract-text>` + `<5 threat-surface categories>` ONLY. The brief MUST NOT include the BA design doc as context.

### 1.4 RT tier vocabulary (mandate #13 (h))

Every external reference cited must carry a Reference-Tier classification:
- **RT0** — PATTERN-only (inspiration; NO source code imported; works for AGPL / GPL viral-defense)
- **RT1** — Source-adapt (compatible-license source adapted; attribution required; e.g. MIT/Apache RT1)
- **RT2** — Binary vendor (binary distributed; not source; e.g. golang binary in subprocess; license per binary)
- **RT3** — Full runtime dependency (pip / npm package; license per package)

References with no RT tier are unclassified — audit-blocking.

### 1.5 Anti-contamination invariant

When an AI agent makes an LLM call, the call site must NOT inject `tools=` / `tool_choice=` at the agent level. These belong 1 layer down in the LLM-client layer. This isolation prevents test contamination + ensures replay determinism.

In arcgentic context: any skill that wraps an LLM call must surface `(system_prompt, user_prompt)` as the agent-facing API, never `(system, user, tools, tool_choice)`.

### 1.6 Cost-discipline (mandate § 4 + § 8.12 (c))

Dev-time tooling MUST NOT consume the founder's separately-billed token quota. Allowed: the AI agent's normal subscription compute; local Ollama; NVIDIA NIM free tier. Banned without explicit opt-in: paid SDK calls (OpenAI / Anthropic / etc.), LLM-as-judge in CI, auto-pull from cloud LLMs.

### 1.7 audit-check mechanical fact verification (mandate #5)

Every audit handoff has a **§ Mechanical audit facts** section with a 4-column markdown table: `| # | Command | Expected | Comment |`. An external script (`audit_check.py` equivalent) runs each command and compares actual vs expected. A round is NOT complete until audit-check reports N/N PASS via `--strict-extended`.

### 1.8 Lesson 8 STRUCTURAL-LAW streak

The codification system itself is observable: each substrate-touching round either preserves the streak (Lesson 8 codification works as expected) or breaks it (codification needs strengthening). Streak is tracked as `{N}-of-{N}` (e.g. 12-of-12); each round either extends (PROVISIONAL → FORMAL after external audit) or resets.

NOVEL preservation types signal that the codification path generalizes; if 3+ rounds of the same NOT-NOVEL type occur, mandate amendment is required.

---

## § 2. Domain vocabulary

Read every definition. arcgentic v0.2.0 implements these primitives.

### 2.1 Round

A discrete unit of development work with explicit scope, 4-commit chain, and audit handoff. Format: `R{phase}.{round}` (e.g. `R1.6.1`) or `R{phase}-{name}` (e.g. `R10-L3-aletheia`).

**Types**:
- **Substrate-touching round** — adds new module class / Protocol surface / event class. Full mandate #17(d) FULL-STRENGTH.
- **Fix round** — narrow correction of a prior round's findings. Mandate #17(d) FULL-STRENGTH but scope-narrowed.
- **Entry-admin** — docs-only governance round opening a new phase/sub-section.
- **Close-admin** — docs-only governance round closing a phase.
- **Meta-admin sweep** — governance backfill (e.g. orphan-file cleanup); rare.

### 2.2 Phase / Sub-round

**Phase**: top-level milestone bucket (e.g. Phase 1 = Event Sourcing Core; Phase 10 = main delivery). Phases close at their own gate; new phases open with entry-admin.

**Sub-round**: hierarchy within a phase — e.g. `R10-L2-finance` (Phase 10 L2 layer, finance vertical) → `R10-L3-aletheia` (Phase 10 L3 layer, aletheia sub-round).

### 2.3 Handoff doc

A markdown doc at `docs/superpowers/plans/{YYYY-MM-DD}-{round-name}-handoff.md` that:
- States round scope, deliverables, mandate posture
- Briefs the dev session for what to build
- Lists 4-commit chain plan
- Specifies audit fact-shape targets

**Sizing** (by scope):
- Full-strength substrate-touching round: 1000-1500 LOC / 16-18 sections
- Narrow fix round: 700-900 LOC / 10-12 sections
- Admin (entry/close): 500-700 LOC / 8-10 sections

See § 7 for templates.

### 2.4 BA design doc

A markdown doc at `docs/design/{ROUND}_BA_DESIGN.md` (uppercase / underscored) that:
- Produces D-1 to D-N named architectural decisions
- Records baseline numeric snapshot + projected deltas (mandate #24)
- Cites references with 4-column triplet table
- File-level decomposition + test plan

See § 8 for template.

### 2.5 Self-audit handoff

A markdown doc at `docs/audits/phase-{P}/{ROUND}.md` written at commit 4 (state refresh) that:
- § 1 Scope summary
- § 2 BA + CR + SE three-way reconciliation (mandate #17(d) clause (h))
- § 7 Mechanical audit facts table (~25-40 facts)
- § 8 Verdict (PASS / NEEDS_FIX)

See § 9 for template.

### 2.6 External audit verdict

A markdown doc at `docs/audits/phase-{P}/{ROUND}-external-audit-verdict.md` written by an external audit-only agent (a separate Claude Opus 4.7 instance for Moirai) that:
- Independently re-runs the 4 quality gates
- Self-verifies its own facts via the same audit-check engine
- Issues PASS / NEEDS_FIX with P0/P1/P2/P3 findings

See § 10 for template.

### 2.7 4-commit chain

The canonical commit sequence for every round. See § 13 for detail. Commits 1+2+4 are docs-only (no code); commit 3 is the only code commit.

### 2.8 Mandate

A standing rule encoded in the project's `AGENTS.md` § 8 (or equivalent). Examples: mandate #20 (SE CONTRACT-ONLY), mandate #21 (license-not-constraint), mandate #25 (CI-substitute discipline). Mandates are amendable but each amendment must be justified by a documented incident.

See § 11 for arcgentic mandate ecosystem.

### 2.9 Forward-debt

A known limitation deferred to a future round, registered in `docs/tech-debt.md` with severity (P0/P1/P2/P3) + owner-round. Format: `| ID | Severity | Description | Owner |`.

Forward-debt aggregate count is tracked across rounds (e.g. "141 cumulative"); net change per round is a quality signal.

### 2.10 Anti-scope

Section in handoff (§ 1.5 typically) explicitly listing what this round does NOT deliver, with rationale. Anti-scope is mechanically verified via audit facts (`grep -r <thing> = 0`).

### 2.11 Audit-check mechanical fact

A row in self-audit § 7 table that mechanically validates a claim:
```
| 1 | cd <repo> && grep -cE 'pattern' file.py | `5` | Description |
```
The `audit_check.py` engine runs each command and compares actual vs expected backtick-wrapped value.

**Strict mode**: `--strict` exits 1 on any FAIL or SKIP.
**Strict-extended mode**: `--strict-extended` ALSO checks AC-1 (Clauses A+B+C — verdict/section/prose claims aligned) + AC-3 (detection-capability vacuity).

### 2.12 Inline-self-finalization (mandate #17(d) clause (h) Option A)

Within a single dev session, three distinct agent personas are dispatched sequentially:
1. **ba-designer** — produces design doc (commit 2)
2. **developer** — implements per design (commit 3)
3. **cr-reviewer** — reviews diff (output → § 2.2 of audit handoff)
4. **se-contract** — reviews threat surfaces (output → § 2.3 of audit handoff)

All in one session. Audit handoff § 2 captures all 3 layers (BA + CR + SE).

### 2.13 RT tier (Reference Tier)

See § 1.4 above. Codified at mandate #13 (h).

### 2.14 Lesson 8 STRUCTURAL-LAW streak

Tracking: `{streak}-of-{streak}` where streak counts consecutive substrate-touching rounds that preserved the codification system without breaking. NOVEL preservation types extend the streak meaningfully; NOT-NOVEL recurrences require mandate amendment.

Mandate #23 (the codification mandate's enforcement clause) is `N/A` for L3-layer substrates because they're not L2 registry — preservation in L3 surfaces via SE NOVEL findings rather than mandate #23's identical-recurrence-prevention.

### 2.15 Anti-contamination invariant

See § 1.5 above. Critical for replay determinism + test hermeticity.

### 2.16 Quality gate (mandate #25)

Local 4-gate run at every code-containing commit (commit 3):
1. `mypy --strict <source-dirs>` → expect `Success: no issues found in N source files`
2. `pytest --tb=no` → expect `N passed`
3. `ruff check .` → expect `All checks passed!`
4. `audit-check <handoff-path> --strict-extended` → expect `N/N PASS + AC-1 + AC-3 PASS`

Mandate #25 (a) = dev-time application (dev session runs gate before push).
Mandate #25 (b) = external audit independent re-run.
Mandate #25 (c)+(d) = handling when CI is unavailable (local 4-gate is canonical).

---

## § 3. IDE adapter layer (NEW — v0.2.0 core abstraction)

arcgentic v0.2.0 must work across VSCode / Cursor / Codex / Claude Code. The adapter layer is the unification surface.

### 3.1 Adapter interface

```python
# arcgentic/adapters/base.py
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentDispatchResult:
    output: str
    exit_code: int
    duration_ms: int
    agent_type: str
    error: str | None = None

@runtime_checkable
class IDEAdapter(Protocol):
    """Adapter for an AI IDE/agent platform.

    Each platform implements this Protocol; arcgentic skills/agents
    invoke platform-agnostic methods, which the adapter translates
    to platform-specific tool calls.
    """

    platform_name: str  # "claude-code" / "cursor" / "vscode-codex" / "codex-cli"

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: str | None = None,  # "worktree" or None
    ) -> AgentDispatchResult:
        """Dispatch a sub-agent.

        agent_name maps to a markdown file at agents/<name>.md
        prompt is the full self-contained brief; agent has zero session context.
        Returns the agent's response text.
        """
        ...

    def invoke_skill(
        self,
        skill_name: str,
        args: str = "",
    ) -> str:
        """Invoke an arcgentic skill in-process.

        skill_name maps to a markdown file at skills/<name>/SKILL.md
        args is the optional argument string for the skill.
        """
        ...

    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def edit_file(self, path: str, old: str, new: str) -> None: ...
    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        """Run a shell command; return (output, exit_code)."""
        ...

    def git_diff_staged(self) -> str: ...
    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        """Returns commit SHA."""
        ...
```

### 3.2 Claude Code adapter (canonical)

Claude Code provides native skill + subagent surfaces. Adapter wraps:
- `dispatch_agent` → `Task` tool with `subagent_type` parameter
- `invoke_skill` → `Skill` tool
- `read_file` → `Read` tool
- `write_file` → `Write` tool
- `edit_file` → `Edit` tool
- `shell` → `Bash` tool

arcgentic's agents register as `~/.claude/agents/<arcgentic-prefix>-<name>.md` (e.g. `arcgentic-planner.md`).
arcgentic's skills register as `~/.claude/skills/arcgentic-<name>/SKILL.md`.

The Claude Code adapter is the canonical reference implementation; other adapters should match its semantic surface.

### 3.3 Cursor adapter

Cursor has no native subagent. Adapter strategies:

**Option A — In-process emulation**: spawn a fresh Cursor agent-session via Cursor's `cmd+K` panel programmatically. Drawback: cumbersome.

**Option B — CLI delegation**: invoke Codex CLI / Claude Code CLI as subprocess. Cleaner.

**Option C — Inline execution**: NO subagent isolation; all 5 agents (planner / developer / ba-designer / cr-reviewer / se-contract) run inline in the same Cursor session, scoped via prompt prefix (e.g. "Acting as ba-designer: ...").

**Recommended for v0.2.0**: Option C with prompt-prefix scoping + manual session-context-reset between agents. Document the loss of isolation.

Cursor-specific files:
- `.cursor/rules/arcgentic.md` — registers arcgentic's discipline + skill list
- `.cursor/agents/` — agent prompts as markdown (Cursor doesn't dispatch, but markdowns are reference material for the session)

### 3.4 VSCode + Codex adapter

VSCode hosts Codex's extension. The Codex API supports subagent dispatch via its sub-task protocol.

Adapter wraps:
- `dispatch_agent` → Codex's `spawn_subtask` API (or equivalent)
- `invoke_skill` → Codex's skill registry (if available) OR inline markdown prompt
- Tool surface → Codex's native tool calls (`run_command` / `read_file` / `edit_file`)

VSCode-specific files:
- `.codex/agents/<name>.md` — agent prompts
- `.codex/skills/<name>/SKILL.md` — skill metadata

### 3.5 Codex CLI adapter

Codex CLI (standalone, no VSCode) is similar to VSCode-Codex but with terminal-native invocation. Adapter wraps Codex CLI's `codex agent dispatch <name> <prompt>` command.

Codex-CLI-specific files: same as VSCode adapter; lives at `~/.codex/agents/` and `~/.codex/skills/`.

### 3.6 Adapter detection (auto-detect)

```python
# arcgentic/adapters/__init__.py
import os
import sys

def detect_adapter() -> "IDEAdapter":
    """Auto-detect which IDE is hosting; return the appropriate adapter."""

    # Claude Code: presence of CLAUDE_CODE_SESSION or ~/.claude/skills
    if os.getenv("CLAUDE_CODE_SESSION") or _has_dir("~/.claude/skills"):
        from .claude_code import ClaudeCodeAdapter
        return ClaudeCodeAdapter()

    # Cursor: presence of CURSOR_SESSION env or .cursor/rules/ in repo
    if os.getenv("CURSOR_SESSION") or _has_dir(".cursor/rules"):
        from .cursor import CursorAdapter
        return CursorAdapter()

    # VSCode + Codex: presence of VSCODE_PID + Codex extension active
    if os.getenv("VSCODE_PID") and _codex_extension_active():
        from .vscode_codex import VSCodeCodexAdapter
        return VSCodeCodexAdapter()

    # Codex CLI: presence of CODEX_SESSION env
    if os.getenv("CODEX_SESSION") or _command_exists("codex"):
        from .codex_cli import CodexCLIAdapter
        return CodexCLIAdapter()

    # Default fallback: inline-execution mode (no subagent isolation)
    from .inline import InlineAdapter
    return InlineAdapter()


def _has_dir(path: str) -> bool:
    return os.path.isdir(os.path.expanduser(path))


def _command_exists(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None


def _codex_extension_active() -> bool:
    # Check VSCode extensions list via VSCode CLI if available
    output, exit_code = _shell("code --list-extensions 2>/dev/null | grep -i codex")
    return exit_code == 0 and bool(output.strip())
```

### 3.7 Adapter-agnostic skill invocation

Skills + agents are written ONCE in arcgentic's markdown format; the adapter translates to platform-specific dispatch:

```python
# Inside any arcgentic skill or hook:
from arcgentic.adapters import detect_adapter

def run():
    adapter = detect_adapter()
    result = adapter.dispatch_agent(
        agent_name="planner",
        prompt=PLANNER_BRIEF.format(round_scope=scope),
    )
    handoff_doc = parse_planner_output(result.output)
    adapter.write_file(handoff_path, handoff_doc)
```

---

## § 4. Skills — detailed spec

### 4.1 plan-round (P0)

**Path**: `arcgentic/skills/plan-round/SKILL.md`
**Trigger**: user invokes `/plan-round <round-name>` or via `arcgentic plan-round` CLI
**Dispatches**: `planner` agent

#### 4.1.1 Purpose

Generate a complete handoff doc for a new round based on round scope + prior-round context. Replaces hand-written handoffs.

#### 4.1.2 Inputs

```yaml
round_name: str  # e.g. "R10-L3-aletheia" or "R1.6.1"
round_type: enum  # "substrate-touching" | "fix-round" | "entry-admin" | "close-admin" | "meta-admin"
prior_round_anchor: str  # full 40-char SHA of prior round's last commit
scope_description: str  # 1-3 sentence scope statement from user
template_size: enum  # "full" (18-section) | "narrow" (10-section) | "admin" (8-section); auto-derived from round_type
```

#### 4.1.3 Algorithm

```
1. Validate inputs:
   a. round_name format matches R-pattern
   b. prior_round_anchor is full 40-char SHA (NOT short)
   c. round_type maps to valid template_size

2. Read prior-round context:
   a. Read prior round's handoff doc (from docs/superpowers/plans/)
   b. Read prior round's audit handoff (from docs/audits/phase-{P}/)
   c. Extract: mandate posture, forward-debt count, Lesson 8 streak state,
      verdict outcome (PASS / NEEDS_FIX), referenced sub-rounds

3. Compute current-state delta:
   a. Lesson 8 streak: prior + 1 if PROVISIONAL → FORMAL; or +1 if substrate-touching
   b. Mandate counter increments (e.g. mandate #25 application count, etc.)
   c. Forward-debt aggregate (prior count + projected new debts)

4. Dispatch planner agent with:
   a. Full brief (see § 5.1)
   b. Round scope, type, prior context, projected mandate posture
   c. Template-size-specific section list

5. Receive planner output:
   a. Validate section count matches template size
   b. Validate all MUST sections present (per § 7.4 conditional matrix)
   c. Run audit-check dry-run on the handoff (no facts yet, but structure-check)

6. Write handoff to docs/superpowers/plans/{date}-{round_name}-handoff.md

7. Optionally also write:
   a. CLAUDE.md § 10 state row update (entry-admin commit will commit this)
   b. Vault current-state.md sync (entry-admin commit will commit this)
```

#### 4.1.4 Outputs

```yaml
handoff_path: str  # written file path
section_count: int
loc: int
mandate_posture_summary: list[str]  # ["#25 (a) 2nd application", "Lesson 8 streak 13-of-13"]
warnings: list[str]  # any MUST-section content marked as TODO
```

#### 4.1.5 Trigger semantics

- User-invoked: `/plan-round <args>` in IDE
- Programmatic: `arcgentic plan-round --round=R10-L3-aletheia --type=substrate-touching --anchor=<sha>`
- Hook-invoked: round-boundary-lesson-scan hook may auto-trigger if it detects an unmarked round transition

#### 4.1.6 Template-size selection

```
substrate-touching → 18-section (§ 7.1)
fix-round → 12-section (§ 7.2)
entry-admin → 10-section (§ 7.3)
close-admin → 10-section (§ 7.3)
meta-admin-sweep → 8-section (§ 7.3)
```

#### 4.1.7 Quality bar

- Every MUST section has minimum content (no `TBD` / `TODO` markers in MUST sections)
- 4-commit chain plan in § 5 is fully specified with concrete file paths
- Reference scan (§ 2) has at least 1 reference row with 4-column triplet
- Mandate compliance plan (§ 7) lists every mandate that applies

#### 4.1.8 SKILL.md content

```markdown
---
name: plan-round
description: Generate a complete round handoff doc from scope + prior-round context. Use when starting a new round (substrate-touching / fix / admin). Replaces hand-written handoffs.
---

# plan-round

Generates a round handoff at `docs/superpowers/plans/{date}-{round}-handoff.md`.

## When to invoke

- User says "let's plan R{N}" or "create handoff for R{N}"
- User invokes `/plan-round <round-name>` slash-command
- New round-name detected without a corresponding handoff doc

## Inputs

`round_name`, `round_type`, `prior_round_anchor` (40-char SHA), `scope_description`.

## Workflow

1. Validate inputs (regex check on round_name; SHA length; round_type enum).
2. Read prior-round handoff + audit handoff via `adapter.read_file()`.
3. Extract prior context (mandate posture, Lesson 8 streak, forward-debt count, last verdict).
4. Dispatch `planner` agent with full brief.
5. Receive planner output; validate sections; write handoff file.
6. Report: handoff_path, section_count, loc, warnings.

## See also

- § 4.1 in arcgentic-v0.2.0-complete-spec.md for full algorithm
- § 5.1 for planner agent contract
- § 7 for handoff doc templates
```

### 4.2 execute-round (P0)

**Path**: `arcgentic/skills/execute-round/SKILL.md`
**Trigger**: user invokes `/execute-round <round-name>` or `arcgentic execute-round`
**Dispatches**: `developer` + `ba-designer` + `cr-reviewer` + `se-contract` agents (sequentially in 4-commit chain pattern)

#### 4.2.1 Purpose

Execute a planned round end-to-end: ship 4 commits, run BA + CR + SE inline-self-finalization, enforce quality gates, write self-audit handoff. Replaces hand-coordinated 4-commit chain.

#### 4.2.2 Inputs

```yaml
round_name: str  # must match an existing handoff at docs/superpowers/plans/{date}-{round}-handoff.md
handoff_path: str  # path to the planned handoff doc
skip_gates: list[str]  # ["pytest", "mypy"] — optional skip flags for development scenarios; default empty
dry_run: bool  # default False; if True, no commits / pushes
```

#### 4.2.3 4-commit chain orchestration

```
Phase 1: Entry-admin (commit 1)
  - Read handoff doc
  - Update CLAUDE.md § state row (mark new round as IN PROGRESS)
  - Update vault current-state.md (§ 11 mandate parity)
  - Stage: handoff + CLAUDE.md + vault sync
  - Run local 4-gate (no-op since no code yet; structure check only)
  - Commit with subject: "docs({round}): entry-admin handoff — {feature} ({position})"
  - Push to origin/main (per project mandate)

Phase 2: BA design pass (commit 2)
  - Dispatch ba-designer agent with brief from handoff § 4
  - Receive BA design doc (markdown)
  - Validate sections: § 0 (round context) / § 1 (reference scan) / § 2 (baseline)
    / § 3+ (architecture w/ D-1 to D-N) / § N (file decomp + test plan)
  - Write design doc to docs/design/{ROUND}_BA_DESIGN.md (uppercase)
  - Run local 4-gate (no-op since no code yet)
  - Commit with subject: "docs({round}/design): BA design pass — {core decisions}"
  - Push to origin/main

Phase 3: Dev body (commit 3)
  - Read BA design doc
  - Dispatch developer agent with brief: implement per BA design § 3 + test plan § N
  - Developer agent produces:
    - Source files (per BA file decomp)
    - Test files (per BA test plan)
    - Inline updates to spec docs (§ in handoff design.md)
    - tech-debt.md entries for forward-debts surfaced during dev
  - Local 4-gate MANDATORY (all 4 must pass):
    a. mypy --strict <source-dirs> → "Success: no issues found in N source files"
    b. pytest --tb=no → "N passed"
    c. ruff check . → "All checks passed!"
    d. audit-check dry-run on handoff (skip since self-audit not written yet)
  - Inline CR step:
    Dispatch cr-reviewer agent with: BASE_SHA + HEAD_SHA + dev diff + brief
    Receive CR findings (P0/P1/P2/P3 + dispositions)
    Address P0/P1 (block on these); P2/P3 can be forward-debts
  - Inline SE step (mandate #20 — CONTRACT-ONLY):
    Extract contract / API surface from BA design + new code
    Dispatch se-contract agent with: contract-text + 5 threat surfaces
    DO NOT pass BA design doc to SE
    Receive SE findings (expect 3-6 NOVEL P3)
    Address blocking findings; register others as forward-debts
  - Commit with subject: "feat({round}): R{N} dev body — {summary}"
  - Push to origin/main

Phase 4: State refresh + audit handoff (commit 4)
  - Refresh CLAUDE.md § state row (mark round as DEV SHIPPED)
  - Sync vault current-state.md
  - Compose self-audit handoff with:
    - § 1 Scope summary
    - § 2.1 BA design pass summary (from Phase 2 output)
    - § 2.2 CR inline pass table (from Phase 3 CR output)
    - § 2.3 SE CONTRACT-ONLY pass table (from Phase 3 SE output)
    - § 3 Toolkit/skill scan
    - § 4 Commits + CI evidence
    - § 5 Quality gates table
    - § 6 Forward-debt delta
    - § 7 Mechanical audit facts (25-40 facts)
    - § 8 Verdict
  - Run audit-check {handoff} --strict-extended
  - If FAIL: iterate fact fixes until N/N PASS + AC-1 + AC-3 PASS
  - Stage: audit handoff + CLAUDE.md + vault sync
  - Commit with subject: "docs(audit/{round}): R{N} self-audit handoff + state refresh"
  - Push to origin/main
```

#### 4.2.4 Failure recovery / retry paths

| Failure point | Retry strategy | Escalation |
|---|---|---|
| BA design produces incomplete sections | Re-dispatch ba-designer with stricter brief + section list | After 2 retries, surface to user |
| Developer code fails mypy --strict | Re-dispatch developer with mypy error context | After 2 retries, surface to user |
| Developer code fails pytest | Re-dispatch developer with failing test names + traceback | After 2 retries, surface to user |
| Developer code fails ruff | Auto-fix via `ruff check --fix` first; if still failing, re-dispatch developer | After 2 retries, surface to user |
| CR finds P0 (blocking) | Address inline (developer re-dispatch with CR feedback); re-run CR | After 2 retries, escalate to user |
| SE finds P0 (blocking) | Address inline (developer re-dispatch with SE feedback); re-run SE | After 2 retries, escalate to user |
| audit-check FAIL on self-audit | Iterate fact fixes (drift detection; expected-value updates) | After 5 fact iterations, escalate |

#### 4.2.5 Quality gate enforcement

The `quality-gate-enforce` hook (see § 6.3) runs at pre-commit. execute-round triggers it programmatically via adapter shell:
```python
result, exit_code = adapter.shell(
    "mypy --strict core/ tests/ && "
    "pytest --tb=no && "
    "ruff check . && "
    "arcgentic audit-check <handoff> --strict-extended",
    timeout_seconds=600,
)
if exit_code != 0:
    raise QualityGateFailure(result)
```

#### 4.2.6 SKILL.md content

```markdown
---
name: execute-round
description: Execute a planned round end-to-end via 4-commit chain with inline BA + CR + SE finalization. Use when handoff doc exists and round is ready to ship.
---

# execute-round

Executes a planned round in 4 commits with inline-self-finalization.

## When to invoke

- User says "execute R{N}" or "ship R{N}"
- User invokes `/execute-round <round-name>` slash-command
- Handoff doc exists at docs/superpowers/plans/{date}-{round}-handoff.md

## Workflow

See § 4.2.3 in arcgentic-v0.2.0-complete-spec.md for 4-phase breakdown.

## Failure recovery

See § 4.2.4 in spec doc.

## Quality gates

See § 4.2.5 + § 6.3 (quality-gate-enforce hook).

## See also

- § 4.2 for full algorithm
- § 5.2 for developer agent
- § 5.3 for ba-designer agent
- § 5.4 for cr-reviewer agent
- § 5.5 for se-contract agent
- § 13 for 4-commit chain canonical
```

### 4.3 codify-lesson (P1)

**Path**: `arcgentic/skills/codify-lesson/SKILL.md`
**Trigger**: round-boundary-lesson-scan hook auto-triggers; or user invokes `/codify-lesson`
**Dispatches**: `lesson-codifier` agent

#### 4.3.1 Purpose

Detect recurring patterns across rounds; promote to STRUCTURAL-LAW lessons; update mandate ecosystem if needed.

#### 4.3.2 3-occurrence detection algorithm

```
1. Scan last N rounds (default N=10) via prior audit handoffs:
   a. Extract from each audit § 6 (forward-debts) the P3 / P2 patterns
   b. Extract from each audit § 2.2 (CR findings) the disposition patterns
   c. Extract from each audit § 2.3 (SE findings) the threat-surface patterns

2. Cluster patterns by similarity:
   a. Lexical: shared keywords (e.g. "anti-contamination" appears in 3+ rounds)
   b. Semantic: pattern shape (e.g. "Protocol field needing SkipValidation" in 3+ rounds)
   c. Use Levenshtein distance + token-overlap for clustering

3. For each cluster with ≥ 3 occurrences:
   a. Promote to PROVISIONAL lesson
   b. Generate Lesson card markdown with: name, definition, examples, prevention rule
   c. Write to lessons/lesson-{N}-{slug}.md

4. For each cluster with ≥ 5 occurrences:
   a. Promote to FORMAL STRUCTURAL-LAW
   b. Generate mandate amendment proposal
   c. Surface to user for review

5. For each prior PROVISIONAL lesson:
   a. If next round preserves (no recurrence of pattern despite similar surface):
      - Increment streak: {N}-of-{N} → {N+1}-of-{N+1}
   b. If next round recurs (pattern shows up again despite Lesson card):
      - Reset streak to 0
      - Trigger mandate amendment review
```

#### 4.3.3 Lesson schema

```yaml
lesson:
  id: int  # e.g. 8
  slug: str  # "structural-law" / "anti-contamination" / etc.
  status: enum  # "DRAFT" | "PROVISIONAL" | "FORMAL" | "RETIRED"
  origin_round: str  # R-name where first observed
  observed_count: int
  preservation_streak: str  # e.g. "12-of-12"
  novel_preservation_types_seen: list[str]
  definition: str  # 1-3 sentences
  examples: list[str]  # round names + line refs
  prevention_rule: str  # actionable
  mandate_amendments_triggered: list[str]  # e.g. ["mandate #23"]
```

#### 4.3.4 lesson-codifier agent contract

See § 5.6.

#### 4.3.5 SKILL.md content

```markdown
---
name: codify-lesson
description: Detect recurring patterns across rounds; promote to STRUCTURAL-LAW lessons; update mandate ecosystem. Use after every round boundary or when 3+ rounds show similar findings.
---

# codify-lesson

Scans last N rounds for recurring patterns; promotes to lessons.

## When to invoke

- After round-boundary-lesson-scan hook fires
- User invokes `/codify-lesson`
- 3+ rounds show same forward-debt or finding pattern

## Algorithm

See § 4.3.2 in arcgentic-v0.2.0-complete-spec.md.

## See also

- § 4.3 for full spec
- § 5.6 for lesson-codifier agent
- § 6.2 for round-boundary-lesson-scan hook
```

### 4.4 track-refs (P1)

**Path**: `arcgentic/skills/track-refs/SKILL.md`
**Trigger**: user invokes `/track-refs` or BA design pass auto-invokes
**Dispatches**: `ref-tracker` agent

#### 4.4.1 Purpose

Maintain `references/INDEX.md` + auto-classify reference RT tier + emit 4-column triplet table for BA design pass.

#### 4.4.2 references/INDEX.md template

```markdown
# references/INDEX.md — categorized scan-friendly index

> {N} indexed reference entries
> Last bulk git pull: {date}
> **Gitignored** — these references are source material; do not import at runtime.
> Vault sister (committable narrative): `vault/01-vision/reference-projects.md`
>
> Maintained per mandate #14 (b). New repos cloned MUST be categorized
> here at landing time. `wc -l references/INDEX.md` is monotone non-decreasing.

---

## How to use this file

```bash
# find all repos tagged with a category
grep -i 'CATEGORY:' references/INDEX.md | grep -i 'atomic-write'

# find all repos relevant to a round
grep 'R10-L3-aletheia-relevance: high' references/INDEX.md
```

Each repo block has:
- **CATEGORY**: tag list (semicolon-separated)
- **Desc**: one line
- **R{current-round}-relevance**: high / medium / low / none
- **Key paths**: where to grep inside the repo

---

## {YYYY-MM-DD} {description} batch

### `{owner}/{repo}` (`references/{dir}/`, {LICENSE})
- **CATEGORY**: tag1; tag2; tag3
- **Desc**: one-line summary
- **R{round}-relevance**: high
- **Key paths**:
  - `path/to/file.py:LN-LM` — what's there
  - `path/to/dir/` — what's in this dir

### `{next-repo}` ...
```

#### 4.4.3 RT tier auto-detection rules

```python
# arcgentic/skills/track-refs/rt_classifier.py
def classify_reference(
    repo_path: str,
    license_str: str,
    usage_evidence: dict,  # {"imported_at_runtime": bool, "binary_vendored": bool,
                          #  "pattern_only": bool, "code_adapted": bool}
) -> str:
    """Return RT tier classification: RT0 / RT1 / RT2 / RT3."""

    if usage_evidence.get("imported_at_runtime"):
        return "RT3"  # full runtime dep
    if usage_evidence.get("binary_vendored"):
        return "RT2"  # binary distributed
    if usage_evidence.get("code_adapted"):
        # Check license compatibility for source adaptation
        if any(viral in license_str.upper() for viral in ["AGPL", "GPL"]):
            return "RT0"  # forced PATTERN-only by viral defense
        return "RT1"  # source-adapt OK
    if usage_evidence.get("pattern_only"):
        return "RT0"

    raise UnclassifiableReference(repo_path)
```

#### 4.4.4 4-column triplet table emit

Used in BA design § 1 reference scan:

```markdown
| # | 用了哪个 | 为什么用 | 用了什么部分 | License + RT |
|---|---|---|---|---|
| 1 | `references/{repo}/{path}:{LN-LM}` + `references/{repo}/LICENSE` | {1-sentence why this beats from-scratch — cite the specific missing pattern} | {pinpoint extracted shape: a regex, 5-line install, function signature, layered diagram, defensive convention} + {what was NOT used} | {LICENSE} + RT{0/1/2/3} |
```

#### 4.4.5 references git fetch flow

```bash
# arcgentic/scripts/fetch-references.sh
#!/usr/bin/env bash
set -euo pipefail

REFS_DIR="${1:-references}"
mkdir -p "$REFS_DIR"

# Pull each cloned repo
for dir in "$REFS_DIR"/*/; do
    if [[ -d "$dir/.git" ]]; then
        echo "=== Pulling $dir ==="
        (cd "$dir" && git pull --ff-only 2>&1 | head -3) || echo "FAILED (skipping)"
    fi
done

# Report
echo ""
echo "=== Index status ==="
echo "Total repos: $(ls -d "$REFS_DIR"/*/ 2>/dev/null | wc -l)"
echo "INDEX.md lines: $(wc -l < "$REFS_DIR/INDEX.md")"
```

#### 4.4.6 ref-tracker agent contract

See § 5.7.

#### 4.4.7 SKILL.md content

```markdown
---
name: track-refs
description: Maintain references/INDEX.md + auto-classify RT tier + emit 4-column triplet table. Use during BA design pass or when adding new reference repo.
---

# track-refs

Maintains references catalog with RT tier classification.

## When to invoke

- BA design pass auto-invokes for reference scan section
- User clones a new reference repo and runs `/track-refs --add <repo>`
- Quarterly refresh: `/track-refs --refresh-all`

## Algorithm

See § 4.4 in arcgentic-v0.2.0-complete-spec.md.

## See also

- § 5.7 for ref-tracker agent
- § 12 for RT tier reference
- § 16 for references/ subsystem
```

### 4.5 cross-session-handoff (P2)

**Path**: `arcgentic/skills/cross-session-handoff/SKILL.md`
**Trigger**: user invokes `/cross-session-handoff <action>`
**Dispatches**: none (helper skill, no agent)

#### 4.5.1 Purpose

Sync state.yaml across multiple AI sessions (e.g. planner session + dev session + audit-only session).

#### 4.5.2 Shared state.yaml medium

**Recommended**: Git-tracked file at `.arcgentic/state.yaml` (in repo root).
**Alternative**: Local shared file at `~/.arcgentic/state.yaml` (cross-repo state).

#### 4.5.3 Lock mechanism

```yaml
# .arcgentic/state.yaml
current_round: "R10-L3-aletheia"
current_phase: "Phase 10"
last_commit: "078f020abc..."  # last commit SHA on main
last_session_id: "dev-session-2026-05-20-T15:00"
locked_by: null  # session ID or null
lock_acquired_at: null  # ISO 8601 timestamp or null
lock_ttl_seconds: 1800  # 30min default
forward_debt_count: 139
lesson_streak: "12-of-12 FORMAL"
mandate_application_counts:
  "25_a": 2
  "25_b": 2
  "24_extension": 4
  "21_license": 6
  "17_d_h_option_a": 8
```

Lock acquisition via atomic file ops (touch + rename) + TTL expiry:
```python
def acquire_lock(state_path: str, session_id: str, ttl: int = 1800) -> bool:
    lock_path = f"{state_path}.lock"
    try:
        with open(lock_path, "x") as f:  # x = exclusive create
            f.write(f"{session_id}\n{int(time.time())}\n{ttl}\n")
        return True
    except FileExistsError:
        # Check TTL expiry
        try:
            content = open(lock_path).read().split("\n")
            existing_session, acquired_at, existing_ttl = content[0], int(content[1]), int(content[2])
            if time.time() - acquired_at > existing_ttl:
                os.unlink(lock_path)
                return acquire_lock(state_path, session_id, ttl)  # retry
        except Exception:
            pass
        return False
```

#### 4.5.4 Algorithm

```
on read():
  1. Try acquire_lock(read-only mode = no lock needed for reads)
  2. Read state.yaml
  3. Return parsed state

on write(updates):
  1. acquire_lock(session_id, ttl=600)  # short TTL for writes
  2. Read current state
  3. Merge updates
  4. Write atomically (tmp file + rename)
  5. Release lock (rm lock_path)

on round_boundary():
  1. acquire_lock(session_id, ttl=1800)
  2. Snapshot state to .arcgentic/state-history/{date}-{round}.yaml
  3. Update current state with new round
  4. Release lock
```

#### 4.5.5 SKILL.md content

```markdown
---
name: cross-session-handoff
description: Sync state.yaml across multiple AI sessions (planner + dev + audit). Use when multiple sessions work on overlapping rounds.
---

# cross-session-handoff

Manages shared .arcgentic/state.yaml with TTL-based locking.

## Commands

- `/cross-session-handoff read` — print current state
- `/cross-session-handoff snapshot` — snapshot current state to history
- `/cross-session-handoff acquire-lock <ttl>` — acquire lock for write
- `/cross-session-handoff release-lock` — release lock manually

## See also

- § 4.5 in arcgentic-v0.2.0-complete-spec.md
```

---

## § 5. Agents — detailed spec

Each agent is a markdown file at `arcgentic/agents/<name>.md` registered with the adapter layer. Agents are stateless (no session memory); every dispatch gets a fully self-contained brief.

### 5.1 planner agent

**File**: `arcgentic/agents/planner.md`
**Dispatched by**: `plan-round` skill
**Expected output**: complete handoff doc markdown

#### 5.1.1 Brief template

```
You are the planner agent for arcgentic round development.

CONTEXT (self-contained):
- Round name: {round_name}
- Round type: {round_type}
- Prior round anchor: {prior_round_anchor}
- Scope description: {scope_description}
- Template size: {template_size}

PRIOR ROUND CONTEXT:
{prior_handoff_summary}  # extracted from prior handoff + audit handoff

CURRENT-STATE DELTAS:
- Forward-debt count: {prior_count} → ~{projected_count} (NEW: {projected_new_count})
- Lesson 8 streak: {prior_streak} → {projected_streak} (preservation type: {preservation_type})
- Mandate application counts: {applicable_mandates}

TASK:
Generate a complete handoff doc for {round_name} using the {template_size} template.

REQUIRED SECTIONS (per § 7.{1|2|3} of arcgentic-v0.2.0 spec):
{section_list}

FOR EACH SECTION:
- Use the prior-round handoff at {prior_handoff_path} as structural reference
- Adapt content to current round's specific scope
- Fill placeholders ({xxx}) with concrete values
- For § 4 BA brief: self-contained brief for ba-designer (zero context assumed)
- For § 5 4-commit chain: file paths + commit subjects + quality gates

QUALITY BAR:
- No `TBD` / `TODO` / `XXX` in MUST sections
- At least 1 reference row with 4-column triplet in § 2
- Concrete file paths (not "various files") in § 5 commit plans
- audit fact-shape targets in § 12 enumerate 25-40 facts

OUTPUT:
The complete handoff doc as markdown. Start with `# {round_name} — Entry-Admin + Dev Handoff` and end with the final `*Entry-admin handoff written by {agent}.*` line.
```

#### 5.1.2 Output validation

After planner returns:
1. Parse markdown headers; count `## ` sections; verify match template
2. Check every MUST section is non-empty (≥ 50 chars body)
3. Verify § 5 4-commit chain has 4 distinct commit blocks
4. Verify § 12 audit fact-shape targets has ≥ 25 enumerated targets
5. Run a structural-dry-run audit-check on the handoff

### 5.2 developer agent

**File**: `arcgentic/agents/developer.md`
**Dispatched by**: `execute-round` skill (Phase 3 — dev body)
**Expected output**: code diff (or file creation commands) + summary of what was changed

#### 5.2.1 Brief template

```
You are the developer agent for arcgentic round implementation.

CONTEXT (self-contained):
- Round: {round_name}
- BA design doc: {ba_design_path} (READ THIS FIRST)
- File-level decomp from BA § N: {file_list}
- Test plan from BA § M: {test_plan}

TASK:
Implement the BA design exactly. Ship code that:
1. Creates each file in BA § N file decomp
2. Adds each test in BA § M test plan
3. Updates any spec docs referenced in BA § design (e.g. PYTHIA_L3_WORLD_MODEL.md § new addendum)
4. Registers any forward-debts surfaced during dev in docs/tech-debt.md

DISCIPLINE:
- TDD: write failing test first, then implementation
- Pydantic v2 frozen + extra=forbid + strict=True for ALL data models
- Anti-contamination: no `tools=` injection at agent code site
- Typed errors only (no raw ValueError / KeyError)
- mypy --strict clean

QUALITY GATES (run before reporting done):
1. `mypy --strict {source-dirs}` → expect 0 errors
2. `pytest --tb=no` → expect 0 failures
3. `ruff check .` → expect "All checks passed!"

FORWARD-DEBT REGISTRATION:
For each known limitation surfaced during dev, add to docs/tech-debt.md Active section:
```
| {ROUND-DEBT-NAME} | **P{0/1/2/3}** | {description with file:line ref} | {owner-round} |
```

OUTPUT:
1. Summary of files created/modified (line counts)
2. Quality gate results (PASS/FAIL for each of 4 gates)
3. Forward-debts registered (if any)
4. Anything that diverged from BA design (with rationale)
```

### 5.3 ba-designer agent

**File**: `arcgentic/agents/ba-designer.md`
**Dispatched by**: `execute-round` skill (Phase 2 — BA design pass)
**Expected output**: complete BA design doc markdown

#### 5.3.1 Brief template

```
You are the ba-designer agent (Backend Architect role).

CONTEXT (self-contained):
- Round name: {round_name}
- Round scope (from handoff § 1.3): {scope}
- Architectural target: {what_to_design}
- Prior round design doc (for reference): {prior_ba_design_path} (if applicable)
- Reference materials available in references/: {reference_subset}

TASK:
Produce a complete BA design doc at docs/design/{ROUND_UPPER}_BA_DESIGN.md.

REQUIRED SECTIONS (per § 8 of arcgentic-v0.2.0 spec):
- § 0 Round context — why this round inserted here
- § 1 Reference scan — 4-column triplet table (per mandate § 8.12 (a)+(e))
- § 2 BA-numeric-claim-snapshot-verify — baseline + projected deltas (per mandate #24)
- § 3 Substrate architecture
- § 4+ Detailed design with named D-1 to D-N decisions
  Each D-N MUST have:
    - Decision: 1 sentence
    - Rationale: 3-5 sentences citing constraints / requirements
    - Alternatives rejected: 1-3 alternatives with why-rejected
- § N File-level decomposition
- § N+1 Test plan
- § N+2 Anti-scope explicit

REFERENCE SCAN RULES:
- For each reference: pinpoint extracted shape, NOT "inspired by generally"
- 4-column triplet: 用了哪个 / 为什么用 / 用了什么部分 / License + RT
- RT classification mandatory (RT0 / RT1 / RT2 / RT3)
- AGPL/GPL repos → RT0 PATTERN-only (viral defense)
- 0 cite-only-VACUOUS allowed

QUALITY BAR:
- No `TBD` / `TODO` in any section
- D-1 to D-N reflect REAL architectural choices (not boilerplate)
- File-level decomp: every file in spec MUST appear in § N
- Test plan: every Protocol method MUST have at least 1 test

OUTPUT:
Complete BA design doc as markdown.
```

### 5.4 cr-reviewer agent

**File**: `arcgentic/agents/cr-reviewer.md`
**Dispatched by**: `execute-round` skill (Phase 3 — inline CR step)
**Expected output**: P0/P1/P2/P3 findings + dispositions table for § 2.2 of audit handoff

#### 5.4.1 Brief template

```
You are the cr-reviewer agent (Code Reviewer role).

CONTEXT (self-contained):
- Round: {round_name}
- Base SHA: {base_sha}  # before dev body
- Head SHA: {head_sha}  # after dev body
- BA design doc: {ba_design_path}  # what was designed
- Dev body diff: {dev_diff}  # what was actually shipped

TASK:
Review the diff for:
1. Correctness (does it implement BA design?)
2. Code quality (Pydantic frozen, typed errors, no anti-contamination violations)
3. Test coverage (does every Protocol method have a test? every error class raised somewhere?)
4. Maintainability (file size, function complexity, naming)
5. Mandate compliance (mandates from handoff § 7)

PRIORITY LEVELS:
- P0 BLOCKING: bug that breaks correctness; round CANNOT proceed
- P1 IMPORTANT: significant quality issue; must address before commit
- P2 NON-BLOCKING: improvement that should land but can be forward-debt
- P3 INFORMATIONAL: observation / suggestion; almost always forward-debt

DISPOSITION OPTIONS:
- Inline-closed: fix inline; cite the fix-commit-line
- Forward-debt: register as docs/tech-debt.md entry; cite future-round
- Disagreed: explain why CR finding doesn't apply; require user concurrence

OUTPUT (markdown table format for § 2.2 of self-audit handoff):

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| CR-1 | P{0/1/2/3} | {1-sentence finding with file:line ref} | {Inline-closed: see commit XYZ / Forward-debt: {DEBT-NAME} / Disagreed: {reason}} |
| CR-2 | ... | ... | ... |

Expected count: 3-7 findings per round.
```

### 5.5 se-contract agent (mandate #20 — CONTRACT-ONLY)

**File**: `arcgentic/agents/se-contract.md`
**Dispatched by**: `execute-round` skill (Phase 3 — inline SE step)
**Expected output**: 3-6 NOVEL P3 findings + dispositions

#### 5.5.1 CRITICAL: input isolation (mandate #20 load-bearing)

**THE SE AGENT MUST NOT RECEIVE THE BA DESIGN DOC AS INPUT.** Passing BA design to SE causes SE to recapitulate known issues (already known to BA). Isolation forces SE to find NOVEL threats.

SE input is ONLY:
- Contract / Protocol / API surface text (extracted from new code)
- 5 threat surface categories (enumerated per round)
- NEW: anti-contamination invariant check
- NEW: cost-discipline check

#### 5.5.2 Brief template

```
You are the se-contract agent (Security Engineer role).

CONTEXT (self-contained):
- Round: {round_name}
- Contract text (Protocol / API / public surface ONLY): {contract_text}
- Threat surface categories to inspect:
  1. {threat_surface_1}  # e.g. "prompt-injection bypass"
  2. {threat_surface_2}  # e.g. "system-prompt leak"
  3. {threat_surface_3}  # e.g. "sycophancy-bypass via clever framing"
  4. {threat_surface_4}  # e.g. "cost-discipline regression"
  5. {threat_surface_5}  # e.g. "decorator-bypass detection"

DISCIPLINE (mandate #20 — CONTRACT-ONLY):
- DO NOT request BA design doc
- DO NOT review code internals (only public surface)
- DO NOT recapitulate BA's already-known issues
- FIND NOVEL threats specific to this round's surface

INVARIANTS TO CHECK:
1. Anti-contamination: agent code MUST NOT inject `tools=` at LLM call site
2. Cost-discipline: NO paid SDK imports outside opt-in paths
3. Replay determinism: pure functions on inputs (no global state mutation)
4. Trust boundary: clear separation between trusted (system) and untrusted (user/agent-generated)

NOVELTY TEST:
For each finding, ask: "Is this finding mentioned in BA design § X.Y?"
If yes → REJECT (CR's job, not SE)
If no → KEEP (NOVEL P3)

OUTPUT (markdown table for § 2.3 of self-audit handoff):

| ID | Sev | Threat surface | Finding | Disposition |
|---|---|---|---|---|
| SE-1 | P{2/3} | {category} | {1-sentence finding} | {Forward-debt {DEBT-NAME} / Inline-closed} |

Expected count: 3-6 NOVEL P3 findings.
```

### 5.6 lesson-codifier agent

**File**: `arcgentic/agents/lesson-codifier.md`
**Dispatched by**: `codify-lesson` skill
**Expected output**: lesson card markdown + mandate amendment proposal (if applicable)

#### 5.6.1 Brief template

```
You are the lesson-codifier agent.

CONTEXT (self-contained):
- Last N rounds analyzed: {round_list}
- Pattern clusters detected: {clusters_with_counts}

TASK:
For each cluster with ≥ 3 occurrences:
1. Promote to PROVISIONAL lesson
2. Generate lesson card markdown:
   - definition (1-3 sentences)
   - examples (round names + line refs)
   - prevention rule (actionable)
3. If ≥ 5 occurrences: also generate mandate amendment proposal

For clusters with preserved streak (no recurrence in latest round):
1. Update existing lesson card with new streak count
2. Update novel_preservation_types_seen list if applicable

OUTPUT:
- For new lessons: lesson card at `lessons/lesson-{N}-{slug}.md`
- For amendments: amendment proposal at `mandates/amendments/{date}-{topic}.md` (user approves before applying)
- For streak updates: updated existing lesson card
```

### 5.7 ref-tracker agent

**File**: `arcgentic/agents/ref-tracker.md`
**Dispatched by**: `track-refs` skill
**Expected output**: INDEX.md update + 4-column triplet table for BA design

#### 5.7.1 Brief template

```
You are the ref-tracker agent.

CONTEXT (self-contained):
- Action: {action}  # "add-new-repo" | "refresh-relevance" | "emit-triplet-for-round"
- Repo path (if add-new-repo): {repo_path}
- Repo metadata: {license, owner, dir_name}
- Usage evidence (for RT classification): {evidence_dict}
- Current round (for relevance tagging): {round_name}

TASK (varies by action):

action=add-new-repo:
1. Compute RT tier via classify_reference()
2. Detect CATEGORY tags from repo contents (README + file extensions + top-level dirs)
3. Generate repo block in INDEX.md format (see § 4.4.2)
4. Append to references/INDEX.md
5. Output: new INDEX.md snippet

action=refresh-relevance:
1. For each repo in INDEX.md, evaluate R{current-round}-relevance
2. Update relevance tags
3. Output: list of changed relevance tags

action=emit-triplet-for-round:
1. For the round's BA design § 1 reference scan
2. For each cited reference, emit 4-column triplet row
3. Output: markdown table snippet ready to inline in BA design
```

---

## § 6. Hooks detailed spec

Hooks are platform-specific event handlers. They live at `.githooks/` for Git hooks, `.claude/hooks/` for Claude Code hooks, `.cursor/hooks/` for Cursor hooks, etc.

### 6.1 pre-commit-fact-check (Git hook)

**Path**: `.githooks/pre-commit`
**Trigger**: every `git commit`
**Purpose**: enforce audit-check on staged audit handoffs

#### 6.1.1 Implementation (bash)

```bash
#!/usr/bin/env bash
# .githooks/pre-commit — fact-check gate
set -euo pipefail

# Find staged audit-handoff markdown files (excluding external-audit-verdicts)
staged_audits=$(git diff --cached --name-only --diff-filter=ACMR \
                | grep -E '^docs/audits/.*\.md$' \
                | grep -vE '-external-audit-verdict\.md$' || true)

if [[ -z "${staged_audits}" ]]; then
    exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
fail_count=0

for audit in ${staged_audits}; do
    echo ""
    echo "=== pre-commit: ${audit} ==="
    if ! arcgentic audit-check "${audit}" --strict-extended; then
        fail_count=$((fail_count + 1))
    fi
done

if (( fail_count > 0 )); then
    echo ""
    echo "pre-commit: ${fail_count} audit handoff(s) failed mechanical check."
    echo "Fix facts, re-stage, retry. (--no-verify to bypass; not recommended.)"
    exit 1
fi

exit 0
```

#### 6.1.2 Installation

```bash
# Install:
git config core.hooksPath .githooks
```

### 6.2 round-boundary-lesson-scan (arcgentic hook)

**Path**: `arcgentic/hooks/round-boundary-lesson-scan.py`
**Trigger**: after `execute-round` finishes Phase 4 (state refresh commit)
**Purpose**: scan last N rounds for recurring patterns; auto-invoke `codify-lesson` if 3+ recurrences detected

#### 6.2.1 Implementation

```python
# arcgentic/hooks/round-boundary-lesson-scan.py
"""Round-boundary lesson-scan hook.

Triggered after every state-refresh commit (Phase 4 of execute-round).
Scans last N rounds for recurring patterns. If 3+ recurrences detected,
auto-invokes codify-lesson skill.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from arcgentic.adapters import detect_adapter
from arcgentic.utils.pattern_detection import (
    scan_last_n_rounds,
    cluster_patterns,
    promote_to_lesson,
)

DEFAULT_N = 10
MIN_OCCURRENCES_FOR_PROVISIONAL = 3
MIN_OCCURRENCES_FOR_FORMAL = 5


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int, default=DEFAULT_N)
    parser.add_argument("--audit-dir", default="docs/audits")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    adapter = detect_adapter()
    rounds = scan_last_n_rounds(args.audit_dir, args.N)
    clusters = cluster_patterns(rounds)

    new_lessons = []
    for cluster in clusters:
        if cluster.occurrence_count >= MIN_OCCURRENCES_FOR_PROVISIONAL:
            if args.dry_run:
                print(f"WOULD promote: {cluster.signature} (count={cluster.occurrence_count})")
            else:
                lesson = adapter.invoke_skill(
                    "codify-lesson",
                    args=f"--cluster='{cluster.signature}'",
                )
                new_lessons.append(lesson)

    if new_lessons:
        print(f"round-boundary-lesson-scan: {len(new_lessons)} new lessons promoted")
    else:
        print(f"round-boundary-lesson-scan: no new patterns (scanned {args.N} rounds)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### 6.3 quality-gate-enforce (post-commit-prep hook)

**Path**: `arcgentic/hooks/quality-gate-enforce.py`
**Trigger**: invoked programmatically by `execute-round` skill at every code-containing commit (Phase 3)
**Purpose**: enforce local 4-gate before allowing push

#### 6.3.1 Implementation

```python
# arcgentic/hooks/quality-gate-enforce.py
"""Quality-gate-enforce hook.

Runs 4 local quality gates before allowing push:
1. mypy --strict
2. pytest --tb=no
3. ruff check .
4. arcgentic audit-check (if audit handoff exists)

Exit 0 if all pass; exit 1 if any fail.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def run_gate(name: str, command: str, timeout: int = 600) -> tuple[bool, str]:
    """Run a quality gate; return (passed, output)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        return (result.returncode == 0, result.stdout + result.stderr)
    except subprocess.TimeoutExpired:
        return (False, f"TIMEOUT after {timeout}s")


def main() -> int:
    gates = [
        ("mypy", "mypy --strict src/ tests/"),
        ("pytest", "pytest --tb=no -q"),
        ("ruff", "ruff check ."),
    ]

    failures = []
    for name, command in gates:
        print(f"=== quality-gate: {name} ===")
        passed, output = run_gate(name, command)
        if passed:
            print(f"  PASS: {output.strip().split(chr(10))[-1]}")  # last line of output
        else:
            print(f"  FAIL: {output[-500:]}")  # last 500 chars
            failures.append(name)

    # audit-check (only if audit handoff was modified)
    audit_files = subprocess.run(
        "git diff --cached --name-only | grep -E '^docs/audits/.*\\.md$' | grep -vE '-external-audit-verdict\\.md$' || true",
        shell=True, capture_output=True, text=True,
    ).stdout.strip().split("\n")
    audit_files = [f for f in audit_files if f]

    for audit in audit_files:
        name = f"audit-check {audit}"
        print(f"=== quality-gate: {name} ===")
        passed, output = run_gate(name, f"arcgentic audit-check {audit} --strict-extended")
        if passed:
            print(f"  PASS: {output.strip().split(chr(10))[-1]}")
        else:
            print(f"  FAIL: {output[-500:]}")
            failures.append(name)

    if failures:
        print(f"\nquality-gate-enforce: {len(failures)} gate(s) failed: {', '.join(failures)}")
        return 1
    print("\nquality-gate-enforce: all gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## § 7. Handoff doc templates

### 7.1 18-section full-strength template (substrate-touching rounds)

```markdown
# {round_name} — Entry-Admin + Dev Handoff

**Phase**: {phase_label}
**Round**: {round_name} (R1)
**Type**: substrate-touching round
**Mandate level**: Mandate #17(d) FULL-STRENGTH; clause (h) Option A {Nth} round
**Prior-round anchor**: `{full_40_char_SHA}` ({prior_round_name})
**Audited HEAD**: forward-deferred to dev-body commit per § 8.11 (a) + (f)
**Audit script**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`
**CI status**: {available | UNAVAILABLE — local-substitute MANDATORY}

---

## 1. Scope
### 1.1 Round identity + prior anchor
### 1.2 Vision anchor — N user-facing examples
### 1.3 Dev body deliverables
### 1.4 Architecture overview — N-layer separation
### 1.5 Anti-scope (NOT delivered this round)
### 1.6 Cost-discipline preserved
### 1.7 Why this round matters
### 1.8 Inherited forward-debt dispositions from prior round

## 2. Reference scan (mandate § 8.12 (a) + (e) + RT vocab #13 (h))

## 3. Toolkit + skill scan (mandate #14)
### 3.1 Skills expected to be invoked
### 3.2 Skills explicitly NOT invoked
### 3.3 MCP / plugin / connector scan
### 3.4 Agency-agents scan
### 3.5 References INDEX scan

## 4. BA design pass brief (dispatch ba-designer agent)
{Inline brief — what BA should produce; reference to § 5.3 contract}

## 5. 4-commit chain plan
### Commit 1 — Entry-admin
### Commit 2 — BA design pass
### Commit 3 — Dev body
### Commit 4 — State refresh + audit handoff
### CI handling per mandate #25 (d)

## 6. Test plan (file-level coverage)
{Table: file | type | tests | coverage focus}

## 7. Mandate compliance plan
### 7.1 Mandate #25 (a)+(b) elevated rigor
### 7.2 Mandate #24 EXTENSION
### 7.3 Mandate #21 license-not-constraint
### 7.4 Mandate #17(d) clause (h) Option A
### 7.5 Mandate #20 SE CONTRACT-ONLY briefing
### 7.6 Mandate #13 clause (h) RT vocabulary
### 7.7 Lesson 8 STRUCTURAL-LAW streak preservation

## 8. ★ Round-specific feature codification 1 (if applicable)

## 9. ★ Round-specific feature codification 2 (if applicable)

## 10. Forward-debt projections
### 10.1 Inherited from prior round
### 10.2 NEW projected forward-debts

## 11. Quality gates per mandate #25 (a) — MANDATORY at every commit
### 11.1 Pre-commit checklist
### 11.2 Failure escalation

## 12. Self-audit fact-shape targets
### 12.1 Commit chain anchors (4 facts)
### 12.2 Substantive code presence (10-12 facts)
### 12.3 Round-specific surface (5-6 facts)
### 12.4 EventLog events (3-5 facts)
### 12.5 Anti-scope grep facts (4-6 facts)
### 12.6 Tests pass + quality gates (5 facts)
### 12.7 Mandate compliance + state row (5-8 facts)

## 13. Audit handoff target path + format

## 14. Security threat surfaces — SE CONTRACT-ONLY brief (mandate #20)
### 14.1 - 14.N (5-6 threat surfaces)

## 15. Why this round matters — strategic summary

## 16. Next round preview

## 17. Open issues / decisions deferred to BA design pass

## 18. Acknowledgments
```

### 7.2 12-section narrow-fix template

```markdown
# {round_name} — Fix-Round Handoff

**Phase**: {phase_label}
**Round**: {round_name} (fix-round for prior {parent_round_name} findings)
**Type**: fix-round (narrow scope)
**Mandate level**: Mandate #17(d) FULL-STRENGTH; scope-narrowed
**Prior-round anchor**: `{full_40_char_SHA}` ({parent_round_name})
**Findings being addressed**: {list of finding-IDs from parent verdict}

---

## 1. Scope (narrow)
### 1.1 Round identity + parent verdict reference
### 1.2 Findings being addressed (1 per finding-ID)
### 1.3 Anti-scope (what NOT to fix even if tempting)

## 2. Reference scan (if any new references needed; usually empty)

## 3. Toolkit scan (per mandate #14)

## 4. Per-finding fix plan
### 4.1 Finding-ID-1: {fix approach}
### 4.2 Finding-ID-2: {fix approach}
### 4.N ...

## 5. 4-commit chain plan
(Same as § 5 in 18-section but smaller-scoped)

## 6. Test plan (additive only; existing tests preserved)

## 7. Mandate compliance plan
(Same as § 7 in 18-section, possibly fewer mandates)

## 8. Forward-debt projections (usually 0 NEW)

## 9. Quality gates per mandate #25 (a)

## 10. Self-audit fact-shape targets (smaller; ~15-20 facts)

## 11. Audit handoff target path + format

## 12. Next round preview
```

### 7.3 10-section admin template (entry-admin / close-admin / meta-admin)

```markdown
# {round_name} — Admin Handoff

**Phase**: {phase_label}
**Round**: {round_name} (admin: {entry-admin | close-admin | meta-admin-sweep})
**Type**: admin (docs-only governance)
**Prior-round anchor**: `{full_40_char_SHA}` ({prior_round_name})

---

## 1. Scope (admin-only; no code)
### 1.1 What this admin round delivers (governance objectives)
### 1.2 What this admin round does NOT touch (anti-scope)

## 2. Files modified
{list of admin docs to update}

## 3. State transitions
{e.g. "Phase 1 ⏳ → ✅", "round R10-L3-aletheia entered IN PROGRESS"}

## 4. Mandate amendments (if any)
{list of mandate updates with vault refs}

## 5. Forward-debt updates
{net change to docs/tech-debt.md; usually closures or transfers}

## 6. 4-commit chain plan (typically 1-2 commits for admin)

## 7. Quality gates (no-op since no code)

## 8. Self-audit fact-shape targets (smaller; ~10-15 facts)

## 9. Audit handoff target path + format

## 10. Next round preview
```

### 7.4 Section conditional matrix

| Section | Substrate (18) | Fix (12) | Admin (10) | Notes |
|---|:---:|:---:|:---:|---|
| 1. Scope | ✅ MUST | ✅ MUST | ✅ MUST | always MUST |
| 2. Reference scan | ✅ MUST | optional | optional | fix-round inherits |
| 3. Toolkit scan | ✅ MUST | ✅ MUST | ✅ MUST | mandate #14 |
| 4. BA brief | ✅ MUST | ⚠️ narrow | ❌ N/A | admin has no BA |
| 5. 4-commit chain plan | ✅ MUST | ✅ MUST | ✅ MUST (1-2 commits) | |
| 6. Test plan | ✅ MUST | optional | ❌ N/A | additive only in fix |
| 7. Mandate compliance | ✅ MUST | ✅ MUST | ✅ MUST | |
| 8-9. Feature codification | conditional | ❌ N/A | ❌ N/A | only when introducing concept |
| 10. Forward-debt projections | ✅ MUST | ✅ MUST | ✅ MUST | |
| 11. Quality gates | ✅ MUST | ✅ MUST | no-op | |
| 12. Audit fact-shape targets | ✅ MUST | ✅ MUST | ✅ MUST | 25-40 / 15-20 / 10-15 |
| 13. Audit handoff target | ✅ MUST | ✅ MUST | ✅ MUST | |
| 14. SE CONTRACT-ONLY brief | ✅ MUST | optional | ❌ N/A | mandate #20 |
| 15. Strategic summary | optional | optional | optional | |
| 16. Next round preview | ✅ MUST | ✅ MUST | ✅ MUST | |
| 17. Open issues | optional | optional | optional | |
| 18. Acknowledgments | optional | optional | optional | |

---

## § 8. BA design doc template

Path: `docs/design/{ROUND_UPPER}_BA_DESIGN.md` (uppercase / underscored).

```markdown
# {ROUND_UPPER}_BA_DESIGN

**Round**: {round_name}
**Author**: ba-designer agent (dispatched by execute-round skill)
**Generated**: {date}
**Round-handoff**: docs/superpowers/plans/{date}-{round}-handoff.md

---

## § 0. Round Context — Why {round_name} Is Inserted Here

{1-2 paragraphs: position in stack, prior round dependencies, what unblocks downstream}

## § 1. Reference Scan (mandate § 8.12 (a) + (e) + RT vocab #13 (h))

### 1.1 References cited (productive)

| # | 用了哪个 | 为什么用 | 用了什么部分 | License + RT |
|---|---|---|---|---|
| 1 | `references/{repo}/{path}:{LN-LM}` | {reason} | {pinpoint extracted} | {LICENSE} + RT{0/1/2/3} |
| 2 | ... | ... | ... | ... |

### 1.2 References REJECTED (with rationale)

- `references/X` — {1-line reject reason}
- `references/Y` — ...

### 1.3 Anti-formalism check

{N productive / M evaluated = X% conversion. 0 cite-only-VACUOUS.}

## § 2. BA-numeric-claim-snapshot-verify (mandate #24 EXTENSION — {Nth} application)

### 2.1 Source-tree numeric claims (baseline `{baseline_SHA}`)

| Claim | Baseline value | Projected delta | Source command |
|---|---|---|---|
| mypy source files | N | +K | `mypy --strict ... \| tail -1` |
| pytest count | M | +J | `pytest --collect-only -q \| tail -1` |
| ruff status | clean | clean | `ruff check .` |
| ... | ... | ... | ... |

### 2.2 Governance + state-row claims (baseline `{baseline_SHA}`)

| Claim | Baseline value | Projected after this round | Source |
|---|---|---|---|
| Forward-debt aggregate | N | N-2 + 4 = N+2 | docs/tech-debt.md |
| Lesson 8 streak | {N}-of-{N} | {N+1}-of-{N+1} | CLAUDE.md § state row |
| Mandate #25 (a) application count | K | K+1 | mandate vault |

## § 3. Substrate Architecture — {Main module / Top-Level}

### 3.1 Module layout (tree)

```
src/
└── {namespace}/
    ├── __init__.py
    ├── {component_a}.py
    ├── {component_b}.py
    └── {sub-dir}/
        ├── __init__.py
        └── {component_c}.py
```

### 3.2 {Primary class A} shape

```python
class {ClassA}(BaseModel):
    """{1-line purpose}"""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    field_a: type_a
    field_b: Annotated[ProtocolField, SkipValidation]  # Protocol not @runtime_checkable

    def method_x(self, ...) -> ReturnType:
        """{behavior}"""
```

### 3.3 {Primary class B} shape

{similar}

### 3.N Decision **D-1**: {decision title}

**Decision**: {1 sentence}

**Rationale**: {3-5 sentences with constraints / requirements cited}

**Alternatives rejected**:
- {alt 1}: {reason rejected}
- {alt 2}: {reason rejected}

### 3.N+1 Decision **D-2**: ...

{continue D-3 to D-N for ~6-10 named decisions}

## § 4. {Feature/Module 2}

{similar substructure to § 3}

## § 5. {Feature/Module 3}

...

## § N. File-Level Decomposition

| File | LOC est. | Responsibility | Key classes |
|---|---|---|---|
| `src/{path}/{a}.py` | ~200 | {1-line} | ClassA, ClassA2 |
| `src/{path}/{b}.py` | ~150 | {1-line} | ClassB |
| ... | ... | ... | ... |

## § N+1. Test Plan

| File | Type | Tests | Coverage focus |
|---|---|---|---|
| `tests/unit/{path}/test_a.py` | unit | ~12 | ClassA happy path + error paths |
| `tests/property/test_x.py` | property | hypothesis | invariants |
| ... | ... | ... | ... |

## § N+2. Anti-scope Explicit

- DO NOT {thing 1} — that's {future round}
- DO NOT {thing 2} — that's {forward-debt}
- DO NOT {thing 3} — out of scope

## § N+3. EventLog Event Surface (if applicable)

{NEW event classes + chain-hash invariant preservation}

## § N+4. Typed Errors

{NEW error hierarchy}
```

---

## § 9. Self-audit handoff template

Path: `docs/audits/phase-{P}/{round}.md`.

```markdown
# {round_name} — Self-Audit Handoff

**Phase**: {phase_label}
**Round**: {round_name}
**Type**: {substrate-touching | fix | admin}
**4-commit chain**:
  - Commit 1 (entry-admin): `{full_40_SHA}`
  - Commit 2 (BA design): `{full_40_SHA}`
  - Commit 3 (dev body): `{full_40_SHA}`
  - Commit 4 (state refresh + this handoff): forward-deferred per § 8.11 (a)+(f)
**Mandate level**: Mandate #17(d) FULL-STRENGTH; clause (h) Option A {Nth} round
**CI status**: {available + run-IDs | UNAVAILABLE — local-substitute applied}
**Verdict claim**: audit-check N/N PASS via `--strict-extended` against this handoff after commit 4

---

## 1. Scope

{1-3 paragraphs summarizing what was delivered per handoff § 1.3}

## 2. Decisions Verified (BA + CR + SE three-way reconciliation per mandate #17(d) clause (h) Option A)

### 2.1 BA design pass (commit `{commit_2_SHA}`; layer 1)

**Decisions made (D-1 to D-N)**:
- D-1: {1-line decision}
- D-2: {1-line decision}
- ...

**RT vocab applied**: {summary of RT0/RT1/RT2/RT3 classifications}

**Baseline-numeric-snapshot deltas verified**: {N of N deltas mechanically verified via audit § 7 facts X-Y}

### 2.2 Code Reviewer inline pass (this commit; layer 2)

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| CR-1 | P{0/1/2/3} | {finding} | {Inline-closed: see commit / Forward-debt {NAME} / Disagreed: {reason}} |
| CR-2 | ... | ... | ... |

Expected: 3-7 findings; all P0 + P1 must be Inline-closed before commit.

### 2.3 Security Engineer CONTRACT-ONLY pass (this commit; layer 3 — mandate #20)

SE brief contained: {N threat surfaces, listed}
SE brief did NOT contain: BA design doc (mandate #20 isolation preserved)

| ID | Sev | Threat surface | Finding | Disposition |
|---|---|---|---|---|
| SE-1 | P{2/3} | {category} | {finding} | {disposition} |
| SE-2 | ... | ... | ... | ... |

Expected: 3-6 NOVEL P3 findings preserving Lesson 8 streak.

## 3. Toolkit + skill scan (mandate #14)

### 3.1 Skills actually invoked
- {skill names + brief evidence}

### 3.2 Skills explicitly NOT invoked (with rationale)
- {skill name}: {why not}

### 3.3 MCP / plugin / connector scan
- {evidence}

## 4. Commits + CI evidence

| # | Commit | SHA | CI | Status |
|---|---|---|---|---|
| 1 | Entry-admin | `{SHA40}` | {run-ID or UNAVAILABLE} | success |
| 2 | BA design | `{SHA40}` | {run-ID} | success |
| 3 | Dev body | `{SHA40}` | {run-ID} | success |
| 4 | This (state refresh) | forward-deferred | pending | pending |

## 5. Quality gates

| Gate | Command | Expected | Result |
|---|---|---|---|
| mypy | `mypy --strict src/ tests/` | `Success: no issues found in N source files` | PASS |
| pytest | `pytest --tb=no` | `N passed` | PASS |
| ruff | `ruff check .` | `All checks passed!` | PASS |
| audit-check | `arcgentic audit-check {this-file} --strict-extended` | N/N PASS + AC-1 + AC-3 PASS | PASS |

## 6. Forward-debts (this round's delta)

### 6.1 Closed

- `{DEBT-NAME}` — closed via commit {SHA40}; verified by fact #{N}

### 6.2 NEW registered

- `{NEW-DEBT-1}` P{0/1/2/3} — {description} — owner: {future round}
- `{NEW-DEBT-2}` ...

### 6.3 Cumulative count

Was {N} (prior round); −{closed} + {NEW} = {N - closed + NEW}.

## 7. Mechanical audit facts

**Verdict-request (AC-1 Clause A)**: This handoff's § 7 contains N facts. Verdict claim: audit-check N/N PASS via `--strict-extended`.

**Verdict-request (AC-1 Clause B)**: Sections referenced (§ N.X fact M format) resolve to facts in correct section.

**Prose claims (AC-1 Clause C)**: Facts 1-N below ground each prose claim:
- fact 1 ({claim}) — {description}
- fact 2 ({claim}) — {description}
- ...

**Verdict-request (AC-3 detection-capability)**: Every fact uses commit-anchored or impl-anchored expected values.

| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | `cd <repo> && git log -1 --format=%H {SHA40}` | `{SHA40}` | Commit 1 anchor |
| 2 | `cd <repo> && git log -1 --format=%H {SHA40}` | `{SHA40}` | Commit 2 anchor |
| ... | ... | ... | ... |
| N | ... | ... | ... |

## 8. Verdict

**Outcome**: PASS / NEEDS_FIX

audit-check N/N PASS via `--strict-extended` + AC-1 Clauses A+B+C PASS + AC-3 PASS.

{N P0/P1/P2 findings; M P3 informational findings as forward-debts}.

Lesson 8 STRUCTURAL-LAW streak: {prior streak} → {new streak} {PROVISIONAL / FORMAL}.

Cumulative forward-debt: {prior count} → {new count}.

Next round: {next round preview}.

---

*Self-audit handoff written by developer agent (mandate #17(d) clause (h) Option A inline-self-finalization, {Nth} round).*
```

---

## § 10. External audit verdict template

Path: `docs/audits/phase-{P}/{round}-external-audit-verdict.md`.

```markdown
# {round_name} R1 — External Audit Verdict ({Auditor agent name} audit-only)

**Outcome**: **PASS** / **NEEDS_FIX**
**Audited dev commit chain**: `{c1_SHA40}` → `{c2_SHA40}` → `{c3_SHA40}` → `{c4_SHA40}`
**Audited self-audit handoff**: `docs/audits/phase-{P}/{round}.md`
**Mechanical reality (audit-check `--strict-extended` re-run by external audit)**: **N PASS / 0 FAIL / 0 SKIP** out of N facts + AC-1 + AC-3 PASS — claim verifies
**Auditor**: {agent identity}
**Audited at**: {YYYY-MM-DD}
**External audit verdict commit**: forward-deferred (this verdict's own SHA anchored by next-round entry-admin)
**Audit script**: `arcgentic audit-check {this-file} --strict-extended`

---

## 1. Executive summary

**PASS / NEEDS_FIX**. {N P0 / N P1 / N P2 / N P3 findings}.

{1-3 paragraphs covering substantive correctness assessment}

**Process correctness**: {STRONG / NEEDS_FIX with details}.

**Lesson 8 STRUCTURAL-LAW streak preservation**: {GENUINELY NOVEL / NOT-NOVEL}. {Reasoning}. Streak: {N}-of-{N} {PROVISIONAL → FORMAL} after this verdict.

## 2. Findings

**{N} P0** — {round rollback / no rollback required}.
**{N} P1** — {blocking / no blocking}.
**{N} P2** — {non-blocking substantive}.
**{N} P3 informational observations** — {non-blocking; documentation / process suggestions}.

### F-{ROUND-EXT-1} — P{N}
**Type**: {category}
**Observation**: {detailed}
**Risk**: {assessment}
**Recommendation**: {actionable}

### F-{ROUND-EXT-2} — P{N}
...

## 3. Special audit attention assessment

### 3.1 {Special attention item 1}
**Verdict**: ✅ {category}
{detail}

### 3.2 ...

## 4. Mandate compliance

| Mandate | Status | Evidence |
|---|---|---|
| #4 cost-discipline | ✅ PASS | {evidence} |
| #5 mechanical audit-fact | ✅ PASS | {evidence} |
| ... | ... | ... |

**Net**: N/N mandate compliance PASS, 0 violations.

## 5. Lesson 8 STRUCTURAL-LAW codification result

**Streak status post-external-audit**: **{N}-of-{N} FORMAL** (no longer provisional).

## 6. Cumulative forward-debt count (external audit confirmation)

External audit independently affirms dev session's tally: {N} cumulative.

## 7. Anti-formalism check

This verdict has N fact rows. All mechanically verifiable. 0 cite-only-VACUOUS.

## 8. {Cross-cutting items if any}

## 9. Mechanical audit facts

**Verdict-request (AC-1 Clause A)**: N facts. Claim: audit-check N/N PASS.
**Verdict-request (AC-1 Clause B)**: ...
**Prose claims (AC-1 Clause C)**: ...
**Verdict-request (AC-3)**: ...

| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | ... | ... | ... |
| N | ... | ... | ... |

## 10. Verdict line

**Outcome**: **PASS / NEEDS_FIX**

{Final summary}

---

*External audit verdict by {Auditor agent name} audit-only planning instance.*
```

---

## § 11. Mandate ecosystem reference

arcgentic v0.2.0 must support these mandate constants. They live at `arcgentic/mandates/registry.yaml`:

```yaml
# arcgentic/mandates/registry.yaml
mandates:
  - id: 1
    name: "Test-First Discipline (TDD)"
    rule: "Write failing test before implementation"
    scope: "all rounds with code"
    enforcement: "mandate-required; verified in audit § 5 quality gates"

  - id: 4
    name: "Cost-discipline"
    rule: "Dev tooling must not consume founder's paid token quota"
    scope: "all rounds"
    enforcement: "mandate-required; verified in audit § 7 anti-scope facts"

  - id: 5
    name: "Mechanical audit-fact verification"
    rule: "Every audit handoff has § 7 fact table; audit-check N/N PASS"
    scope: "all rounds"
    enforcement: "pre-commit hook + execute-round Phase 4"

  - id: 13
    name: "RT tier vocabulary"
    clause: "(h)"
    rule: "Every reference cited carries RT0/RT1/RT2/RT3 classification"
    scope: "all rounds with reference scan"
    enforcement: "BA design § 1 reference scan table column"

  - id: 14
    name: "Toolkit + skill scan discipline"
    clauses: "(a), (b)"
    rule: "Handoff § 3 enumerates skills/MCP/agents to be invoked; audit § 3 reports actual"
    scope: "all rounds"
    enforcement: "audit § 3"

  - id: 17
    name: "Subagent dispatch discipline"
    clauses: "(d)", "(h)"
    rule: "Mandate-level work uses agency-agents; clause (h) Option A = inline-self-finalization"
    scope: "all substrate-touching rounds"
    enforcement: "audit § 2 BA + CR + SE three-way reconciliation"

  - id: 20
    name: "SE CONTRACT-ONLY briefing"
    rule: "SE brief contains threat surfaces DIRECT, NOT BA-derived; load-bearing isolation"
    scope: "all substrate-touching rounds"
    enforcement: "audit § 2.3 brief composition check"

  - id: 21
    name: "License-not-constraint"
    rule: "AGPL/GPL viral defense via RT0 PATTERN-only; MIT/Apache RT1 source-adapt OK"
    scope: "rounds citing references"
    enforcement: "BA § 1 RT classification + audit anti-scope facts"

  - id: 24
    name: "EXTENSION baseline-numeric-snapshot-verify"
    rule: "BA design § 2 records baseline + projected deltas; audit § 7 verifies mechanically"
    scope: "all substrate-touching rounds"
    enforcement: "BA § 2 + audit § 7 fact rows 1-N"

  - id: 25
    name: "CI-substitute discipline"
    clauses: "(a), (b), (c), (d)"
    rule: "Local 4-gate canonical when CI unavailable; (a)=dev-time, (b)=external re-run"
    scope: "all code-containing rounds"
    enforcement: "Phase 3 of execute-round + audit § 5"

lessons:
  - id: 8
    name: "STRUCTURAL-LAW"
    status: "FORMAL"
    rule: "Codification system observability: each round preserves or breaks streak"
    streak_format: "{N}-of-{N}"
    preservation_types: list of NOVEL preservation types seen
    enforcement: "audit § 8 streak status reporting"
```

### 11.1 Adding new mandates

When a new round surfaces a pattern that warrants codification (3+ occurrences detected by codify-lesson skill):
1. lesson-codifier proposes mandate amendment at `mandates/amendments/{date}-{topic}.md`
2. User reviews + approves
3. arcgentic toolkit applies amendment: appends to `mandates/registry.yaml` + updates AGENTS.md (or equivalent for arcgentic)
4. Lesson card updated with `mandate_amendments_triggered`

---

## § 12. RT tier classification reference

### 12.1 RT0 — PATTERN-only

**When to use**:
- AGPL-3.0 / GPL-3.0 sources (viral-defense forced)
- Inspirations not directly imported (architectural patterns)

**Rules**:
- ZERO imports from the reference repo at runtime
- ZERO source files copied (even with attribution)
- Only the PATTERN extracted: a regex shape, a workflow shape, an algorithm shape, a defensive convention

**Audit fact**:
```
| N | bash -c "grep -rE 'from {repo_name}|import {repo_name}' src/ tests/ | wc -l" | `0` | RT0 PATTERN-only: NO source imports |
```

### 12.2 RT1 — Source-adapt

**When to use**:
- MIT / Apache-2.0 / BSD / similar compatible licenses
- Source code adapted (with attribution) into our codebase

**Rules**:
- Attribution required in BA § 1 reference scan + module docstring
- Modifications allowed
- License compliance enforced

**Audit fact**:
```
| N | grep -c "Adapted from {repo_name} (License: {LIC})" src/{path}.py | `1` | RT1 source-adapt attribution |
```

### 12.3 RT2 — Binary vendor

**When to use**:
- Distributing a compiled binary (e.g. Go binary in Python subprocess)
- License must permit binary redistribution

**Rules**:
- Binary version pinned at SHA-256
- Install script verifies SHA before use
- Binary lives at known path (e.g. `bin/cliproxy`)

**Audit fact**:
```
| N | sha256sum bin/{binary} | awk '{print $1}' | `{expected_sha256}` | RT2 binary vendor SHA verification |
```

### 12.4 RT3 — Full runtime dependency

**When to use**:
- Standard pip / npm / cargo package
- License per package; respected by package manager

**Rules**:
- Pinned version in pyproject.toml / requirements.txt
- License audited at package add time

**Audit fact**:
```
| N | grep '^{package_name} =' pyproject.toml | `{package_name} = "X.Y.Z"` | RT3 pinned version |
```

---

## § 13. 4-commit chain canonical

### 13.1 Commit 1 — Entry-admin

**Subject**: `docs({round}): entry-admin handoff — {feature description} ({Nth} L{layer} sub-round)`

**Files modified**:
- `docs/superpowers/plans/{date}-{round}-handoff.md` (NEW)
- `CLAUDE.md` (or `AGENTS.md`) — § state row update
- `vault/00-current-state.md` (§ 11 mandate parity sync if vault used)

**Code**: NO

**Quality gate**: no-op (mypy/pytest/ruff/audit-check all check nothing changed in code)

**Commit message body template** (per § 4.1.8 above).

### 13.2 Commit 2 — BA design pass

**Subject**: `docs({round}/design): BA design pass — {core decisions summary}`

**Files modified**:
- `docs/design/{ROUND_UPPER}_BA_DESIGN.md` (NEW)

**Code**: NO

**Quality gate**: no-op

**Commit message body**:
```
D-1 through D-N decisions. {N}-layer separation. {N}-reference triplet table
({references}). {N} projected baseline deltas per mandate #24 EXTENSION.
Anti-scope explicit.

No code yet; design doc only.
```

### 13.3 Commit 3 — Dev body

**Subject**: `feat({round}): R{N} dev body — {1-line summary}`

**Files modified**:
- All source files per BA § N file decomp
- All test files per BA § M test plan
- Spec docs referenced in BA § design.md
- `docs/tech-debt.md` (forward-debts registered)

**Code**: YES (the only code-containing commit)

**Quality gate**: MANDATORY 4-gate before push:
```bash
mypy --strict src/ tests/ && \
pytest --tb=no && \
ruff check . && \
arcgentic audit-check <handoff> --strict-extended-dry-run  # facts not written yet; structure check
```

**Commit message body**:
```
{Summary 2-3 paragraphs}

Implements {what} per BA design § X.Y.

NEW substrate: src/{path}/ (~N LOC across M source files)
NEW typed errors: {names}
NEW EventLog events: {N} {prefix}* classes (chain-hash preserved via SUPERSET)
NEW tests: M test files / N default + K gated

Founder mandate {ID} embodied: "{quote if applicable}"

Mandate #25 (a) local 4-gate verified before push: mypy --strict / pytest / ruff / audit-check.

Reference cites per § 8.12 (a) + (e):
- {ref 1} ({LICENSE} RT{N})
- {ref 2} ({LICENSE} RT{N})
```

### 13.4 Commit 4 — State refresh + audit handoff

**Subject**: `docs(audit/{round}): R{N} self-audit handoff + state refresh`

**Files modified**:
- `docs/audits/phase-{P}/{round}.md` (NEW; ~25-40 facts)
- `CLAUDE.md` (or `AGENTS.md`) — § state row refresh
- `vault/00-current-state.md` sync

**Code**: NO

**Quality gate**: `audit-check {handoff} --strict-extended` MUST be N/N PASS + AC-1 + AC-3 PASS.

**Commit message body**:
```
Self-audit with ~N mechanical facts covering:
  - Substrate code presence ({M} source files / {K} typed errors / {L} events)
  - Tests count and pass-rate
  - Mandate compliance ({list})
  - Reference triplets ({N} productive)
  - Anti-scope grep facts ({M} zero-match)

Audit-check N/N PASS via --strict-extended (claim verified by external
audit independent re-run per mandate #25 (b)).

State refresh + vault sync per § 11 mandate.

Lesson 8 streak {N}-of-{N} PROVISIONAL (external audit will close to FORMAL).
```

---

## § 14. Audit-check engine spec

arcgentic's `audit-check` command parses + verifies markdown audit handoffs.

### 14.1 Fact-table parser

Input: markdown file with § 7 (or similar) containing a fact table:
```
| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | `cmd ...` | `expected-value` | description |
```

Parse rules:
- Row regex: `^\|\s*(?P<id>[0-9a-z]+)\s*\|\s*\`(?P<command>.+?)\`\s*\|\s*(?P<expected>.+?)\s*\|\s*(?P<observed>.+?)\s*\|$`
- Recognized command prefixes: `cd `, `git `, `uv run `, `bash `, `arcgentic ` (and equivalents for the project)
- Expected value: first backtick-wrapped string in expected column
- Unescape `\|` → `|` in command field (markdown-cell pipe-escape)

### 14.2 Clauses A/B/C semantics (mandate AC-1)

**Clause A — verdict-claim consistency**:
- Find verdict-claim like "audit-check N/M PASS"
- Verify N == M == actual fact-row count

**Clause B — section-reference resolution**:
- Find prose refs like "§ N.X fact Y"
- Verify fact Y exists in section N.X (parse `### N.X` headers + their body's fact-IDs)

**Clause C — prose-claim numeric match**:
- Find prose claims like "fact M (... = K)"
- Verify §7 fact M's expected value == K (after stripping inline backticks)

### 14.3 AC-3 detection-capability

For each fact, verify the expected value would actually catch a drift:
- Expected values must be commit-anchored (40-char SHA) or impl-anchored (specific count, specific string)
- Anti-pattern: `≥ N` (no upper bound; doesn't detect over-count)
- Anti-pattern: `1` for a non-zero count (would pass for any non-zero; should anchor exact expected)

### 14.4 Implementation reference

Full reference Python implementation:

```python
# arcgentic/audit_check.py
"""arcgentic audit-check — mechanical fact verification engine.

Modeled after Moirai's audit_check.py (which it inspired).
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass


_ROW_RE = re.compile(
    r"^\|\s*(?P<id>[0-9a-z]+)\s*\|\s*`(?P<command>.+?)`\s*\|"
    r"\s*(?P<expected>.+?)\s*\|\s*(?P<observed>.+?)\s*\|$",
    re.M,
)
_BACKTICK_VALUE_RE = re.compile(r"`([^`]+)`")
_RECOGNIZED_PREFIXES = ("cd ", "git ", "uv run ", "bash ", "arcgentic ")
_NO_OUTPUT_PATTERNS = ("(no output", "(empty", "(no rows", "(no diff")


@dataclass
class FactResult:
    fact_id: str
    command: str
    expected: str
    actual: str
    passed: bool
    exit_code: int


def parse_facts(audit_path: Path) -> list[tuple[str, str, str]]:
    """Parse facts from audit § 7. Returns [(id, command, expected), ...]."""
    text = audit_path.read_text()
    facts = []
    for match in _ROW_RE.finditer(text):
        fact_id = match.group("id")
        command = match.group("command").replace("\\|", "|")
        expected_cell = match.group("expected")
        bt_match = _BACKTICK_VALUE_RE.search(expected_cell)
        if not bt_match:
            continue
        expected = bt_match.group(1)
        if not any(command.startswith(p) for p in _RECOGNIZED_PREFIXES):
            continue
        facts.append((fact_id, command, expected))
    return facts


def run_fact(fact_id: str, command: str, expected: str, timeout: int = 120) -> FactResult:
    """Run a fact's command; compare to expected."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        actual = result.stdout.rstrip("\n")
        exit_code = result.returncode

        if any(p in expected for p in _NO_OUTPUT_PATTERNS):
            passed = not actual.strip()
        elif expected == actual or expected.strip() == actual.strip():
            passed = True
        else:
            passed = False

        return FactResult(fact_id, command, expected, actual, passed, exit_code)
    except subprocess.TimeoutExpired:
        return FactResult(fact_id, command, expected, f"TIMEOUT after {timeout}s", False, -1)


def check_ac1(audit_path: Path) -> tuple[bool, list[str]]:
    """AC-1 Clauses A+B+C check."""
    errors = []
    text = audit_path.read_text()

    # Strip inline backticks for prose-filter
    prose = "\n".join(line for line in text.split("\n") if not line.startswith("|"))
    prose_filtered = re.sub(r"`[^`]*`", "", prose)

    # Parse fact-row map: fact-id → expected literal (numeric only)
    fact_count = len(re.findall(r"^\| \d+ \| `", text, re.M))
    fact_rows = dict(re.findall(r"^\| (\d+) \| `[^`]+` \| `(\d+)` \|", text, re.M))

    # Clause A: verdict-claim N/N matches fact_count
    verdict_claims = re.findall(r"audit-check (\d+)/(\d+) PASS via `--strict`", text)
    if not verdict_claims:
        errors.append("Clause A: no verdict-request claim found")
    else:
        last_n, last_total = verdict_claims[-1]
        if not (int(last_n) == int(last_total) == fact_count):
            errors.append(f"Clause A: verdict-request {last_n}/{last_total} does not match §7 fact-row count {fact_count}")

    # Clause B: every § N.X fact M ref resolves
    refs = re.findall(r"§\s*(\d+\.\d+)\s+fact\s+(\d+)", prose_filtered)
    subsections: dict[str, set[int]] = {}
    for part in re.split(r"(?:^|\n)### ", text)[1:]:
        sec_match = re.match(r"(\d+\.\d+)", part)
        if sec_match is not None:
            subsections[sec_match.group(1)] = {int(x) for x in re.findall(r"^\| (\d+) \|", part, re.M)}
    bad_refs = [(s, m) for s, m in refs if int(m) not in subsections.get(s, set())]
    if bad_refs:
        errors.append(f"Clause B: {len(bad_refs)} prose ref(s) point to non-existent section+fact pair: {bad_refs[:5]}")

    # Clause C: every fact M (... = K) prose claim matches §7 fact-M expected
    claims_c = re.findall(r"fact (\d+) \([^)]*= (\d+)\)", prose_filtered)
    mismatches_c = [(m, k) for m, k in claims_c if fact_rows.get(m) != k]
    if mismatches_c:
        errors.append(f"Clause C: {len(mismatches_c)} prose claim(s) mismatch §7 expected: {mismatches_c[:5]}")

    return (not errors, errors)


def check_ac3(audit_path: Path) -> tuple[bool, list[str]]:
    """AC-3 detection-capability check."""
    errors = []
    text = audit_path.read_text()
    # Anti-pattern: `≥ N` or `>= N` in expected values
    fact_expected_values = re.findall(r"^\| \d+ \| `[^`]+` \| `([^`]+)` \|", text, re.M)
    for ev in fact_expected_values:
        if "≥" in ev or ">=" in ev:
            errors.append(f"AC-3: fact has unbounded expected '{ev}' — drift not detectable")
    return (not errors, errors)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_file")
    parser.add_argument("--strict", action="store_true", help="exit 1 on FAIL or SKIP")
    parser.add_argument("--strict-extended", action="store_true", help="strict + AC-1 + AC-3")
    args = parser.parse_args(argv)

    audit_path = Path(args.audit_file)
    facts = parse_facts(audit_path)

    if not facts:
        print(f"audit_check: no fact rows found in {audit_path}")
        return 0

    fail = 0
    skip = 0
    for fact_id, command, expected in facts:
        print(f"\n--- fact {fact_id} ---")
        print(f"command : {command}")
        print(f"expected: `{expected}`")
        result = run_fact(fact_id, command, expected)
        print(f"rc      : {result.exit_code}")
        print(f"actual  : {result.actual!r}")
        if result.passed:
            print(f"verdict : PASS")
        else:
            if "TIMEOUT" in result.actual:
                skip += 1
                print(f"verdict : SKIP ({result.actual})")
            else:
                fail += 1
                print(f"verdict : FAIL (expected '{expected}')")

    total = len(facts)
    passed = total - fail - skip
    print(f"\n=== summary: {total} fact rows, {passed} pass / {fail} fail / {skip} skip ===")

    if args.strict_extended:
        ac1_ok, ac1_errors = check_ac1(audit_path)
        print(f"\n=== fact-shape #20 (AC-1, Clauses A+B+C) ===")
        if ac1_ok:
            print("PASS — Clauses A+B+C all hold AND Clause C non-vacuous")
        else:
            for e in ac1_errors:
                print(f"FAIL — {e}")

        ac3_ok, ac3_errors = check_ac3(audit_path)
        print(f"\n=== detection-capability (AC-3) ===")
        if ac3_ok:
            print("PASS — all detection-capability subsection facts expect drift detection")
        else:
            for e in ac3_errors:
                print(f"FAIL — {e}")

        if not (ac1_ok and ac3_ok):
            return 1

    if args.strict and (fail > 0 or skip > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

---

## § 15. Lesson 8 STRUCTURAL-LAW protocol

### 15.1 Observable behavior

The codification system itself is observable. Each round either:
- **Preserves the streak**: pattern that would have failed-by-recurrence DOES NOT recur, despite similar surface
- **Breaks the streak**: pattern recurs, indicating codification needs strengthening

### 15.2 Streak format

`{N}-of-{N}` where N counts consecutive substrate-touching rounds that preserved.

State transitions:
- After dev session ships: `{prior}-of-{prior} FORMAL` → `{prior+1}-of-{prior+1} PROVISIONAL`
- After external audit PASS: `PROVISIONAL → FORMAL`
- After recurrence detected: reset to 0; trigger mandate amendment

### 15.3 NOVEL preservation types

Each round's preservation may be:
- **NOVEL preservation type**: the codification path applied to a structurally-new scope (e.g. "language-boundary scope" → "multi-agent-orchestration scope" → "llm-behavior-constraint scope")
- **NOT-NOVEL preservation**: same scope as prior round; less informative but still valid

3+ consecutive NOT-NOVEL preservations signal that the codification path may be plateauing — review whether new scopes should be exercised.

### 15.4 Mandate #23 N/A clause (L3-layer)

L3-layer (e.g. arcgentic's `core/pythia/l3/*` equivalent) substrates are NOT L2 registry; mandate #23's identical-recurrence-prevention mechanism does NOT apply. Preservation in L3 surfaces is via:
- SE CONTRACT-ONLY findings (NOVEL P3 per round, per mandate #20)
- Cross-round semantic novelty

If 3+ consecutive L3 rounds have 0 NOVEL P3 SE findings, that's the signal that L3 codification has plateaued — review.

### 15.5 Lesson card format

```yaml
# lessons/lesson-8-structural-law.md
---
id: 8
slug: structural-law
status: FORMAL
origin_round: R4.6.2
observed_count: 12
preservation_streak: "12-of-12"
novel_preservation_types_seen:
  - "single-vertical-scope"
  - "multi-vertical-scope"
  - "multi-source-scope"
  - "language-boundary-scope"
  - "multi-agent-orchestration-scope"
mandate_amendments_triggered:
  - "mandate #23"  # codification enforcement
  - "mandate #23-multi-source"
  - "mandate #25"
---

# Lesson 8 — STRUCTURAL-LAW

## Definition

The codification system itself is observable. Each substrate-touching round
either preserves the streak (codification works as expected) or breaks it
(codification needs strengthening). Streak format: {N}-of-{N}.

## Examples

- R10-L2-finance: 1-of-1 PROVISIONAL → 1-of-1 FORMAL after audit
- R10-L2-weather: 2-of-2 PROVISIONAL → 2-of-2 FORMAL ...
- R10-L3-aletheia: 12-of-12 FORMAL → 13-of-13 PROVISIONAL (NEW preservation type: llm-behavior-constraint)

## Prevention rule

For each substrate-touching round:
1. Before round: predict whether preservation type is NOVEL or NOT-NOVEL
2. After round: external audit confirms or rejects the prediction
3. If 3+ consecutive NOT-NOVEL: review whether new scope dimension should be exercised
4. If recurrence: increment recurrence counter; if 3+, trigger mandate amendment
```

---

## § 16. references/ subsystem

### 16.1 Directory structure

```
references/
├── INDEX.md                  # gitignored; categorized index
├── papers/                   # gitignored; PDF research papers
│   ├── paper1.pdf
│   └── paper2.pdf
├── repo1/                    # gitignored; git clone of upstream
│   ├── .git/
│   ├── LICENSE
│   └── ...
├── repo2/
└── ...
```

### 16.2 Gitignore configuration

```
# .gitignore
references/
```

### 16.3 References management

- **Clone**: `(cd references && git clone https://github.com/owner/repo)`
- **Update**: `(cd references/repo && git pull --ff-only)`
- **Bulk update**: `scripts/fetch-references.sh`
- **Remove**: `rm -rf references/repo` + remove block from INDEX.md

### 16.4 INDEX.md maintenance

- Updated at clone time (mandatory; ref-tracker agent automates)
- Updated at every round boundary for relevance tags
- Monotone non-decreasing line count (audit fact)

### 16.5 Vault sister (committable narrative)

A narrative version of INDEX.md lives committed at `vault/01-vision/reference-projects.md` (or equivalent). Less detailed; per-relationship descriptions; includes long-term strategic notes about references. The vault sister is the user-facing narrative; INDEX.md is the grep-friendly catalog.

---

## § 17. Quality gates spec

### 17.1 mypy --strict configuration

```toml
# pyproject.toml
[tool.mypy]
strict = true
python_version = "3.13"
files = ["src/", "tests/"]
exclude = ["build/", "dist/", "references/"]

# Pydantic v2 requires:
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

### 17.2 pytest discovery + organization

```
tests/
├── unit/              # fast; mock LLMs; no network
│   ├── {module}/test_a.py
│   └── ...
├── property/          # hypothesis-driven
│   └── test_*.py
└── integration/       # slow; gated; real backend
    └── test_*.py
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--strict-markers"
markers = [
    "integration: slow integration tests (deselect with '-m \"not integration\"')",
    "stress: long-running stress tests (deselect with '-m \"not stress\"')",
]
```

### 17.3 ruff configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py313"
exclude = ["build/", "dist/", "references/"]

[tool.ruff.lint]
select = [
    "E", "W", "F",  # default
    "I",            # isort
    "UP",           # pyupgrade
    "B",            # bugbear
    "A",            # builtins
    "N",            # pep8-naming
]
ignore = []
```

### 17.4 audit-check integration

audit-check is `arcgentic audit-check` (installed via pyproject.toml entry point):

```toml
# pyproject.toml
[project.scripts]
arcgentic = "arcgentic.cli:main"
```

```python
# arcgentic/cli.py
import argparse
from .audit_check import main as audit_check_main

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    audit_check_parser = subparsers.add_parser("audit-check")
    audit_check_parser.add_argument("audit_file")
    audit_check_parser.add_argument("--strict", action="store_true")
    audit_check_parser.add_argument("--strict-extended", action="store_true")

    plan_round_parser = subparsers.add_parser("plan-round")
    plan_round_parser.add_argument("round_name")
    plan_round_parser.add_argument("--type", required=True)
    plan_round_parser.add_argument("--anchor", required=True)

    execute_round_parser = subparsers.add_parser("execute-round")
    execute_round_parser.add_argument("round_name")

    args = parser.parse_args()

    if args.command == "audit-check":
        return audit_check_main([args.audit_file] +
                                (["--strict"] if args.strict else []) +
                                (["--strict-extended"] if args.strict_extended else []))
    elif args.command == "plan-round":
        from .skills.plan_round import run
        return run(args)
    elif args.command == "execute-round":
        from .skills.execute_round import run
        return run(args)
    else:
        parser.print_help()
        return 1
```

---

## § 18. File structure for arcgentic v0.2.0

```
arcgentic/
├── pyproject.toml
├── README.md
├── LICENSE
├── .githooks/
│   └── pre-commit                          # § 6.1
├── arcgentic/                              # Python package
│   ├── __init__.py
│   ├── cli.py                              # § 17.4
│   ├── audit_check.py                      # § 14.4
│   ├── adapters/                           # § 3 IDE adapter layer
│   │   ├── __init__.py                     # detect_adapter()
│   │   ├── base.py                         # IDEAdapter Protocol
│   │   ├── claude_code.py
│   │   ├── cursor.py
│   │   ├── vscode_codex.py
│   │   ├── codex_cli.py
│   │   └── inline.py                       # fallback (no subagent isolation)
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── plan_round.py                   # § 4.1
│   │   ├── execute_round.py                # § 4.2
│   │   ├── codify_lesson.py                # § 4.3
│   │   ├── track_refs.py                   # § 4.4
│   │   └── cross_session_handoff.py        # § 4.5
│   ├── agents/
│   │   ├── planner.md                      # § 5.1
│   │   ├── developer.md                    # § 5.2
│   │   ├── ba_designer.md                  # § 5.3
│   │   ├── cr_reviewer.md                  # § 5.4
│   │   ├── se_contract.md                  # § 5.5
│   │   ├── lesson_codifier.md              # § 5.6
│   │   └── ref_tracker.md                  # § 5.7
│   ├── hooks/
│   │   ├── round_boundary_lesson_scan.py   # § 6.2
│   │   └── quality_gate_enforce.py         # § 6.3
│   ├── templates/                          # markdown templates
│   │   ├── handoff_18_section.md           # § 7.1
│   │   ├── handoff_12_section.md           # § 7.2
│   │   ├── handoff_10_section.md           # § 7.3
│   │   ├── ba_design.md                    # § 8
│   │   ├── self_audit_handoff.md           # § 9
│   │   └── external_audit_verdict.md       # § 10
│   ├── mandates/
│   │   ├── registry.yaml                   # § 11
│   │   └── amendments/                     # future amendments land here
│   ├── lessons/
│   │   └── lesson-8-structural-law.md      # § 15.5
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── pattern_detection.py            # used by codify-lesson
│   │   ├── rt_classifier.py                # used by track-refs
│   │   └── git_helpers.py
│   └── state/                              # cross-session state
│       └── state.yaml                      # § 4.5.2
├── tests/
│   ├── unit/
│   │   ├── adapters/
│   │   │   ├── test_claude_code.py
│   │   │   ├── test_cursor.py
│   │   │   └── test_detect.py
│   │   ├── skills/
│   │   │   ├── test_plan_round.py
│   │   │   ├── test_execute_round.py
│   │   │   ├── test_codify_lesson.py
│   │   │   └── test_track_refs.py
│   │   ├── hooks/
│   │   │   ├── test_round_boundary_lesson_scan.py
│   │   │   └── test_quality_gate_enforce.py
│   │   └── test_audit_check.py
│   ├── property/
│   │   ├── test_pattern_detection_properties.py
│   │   └── test_rt_classifier_properties.py
│   ├── integration/
│   │   ├── test_end_to_end_round.py        # full 4-commit chain integration
│   │   └── test_audit_check_real_handoff.py
│   └── fixtures/
│       ├── sample_handoff_18_section.md
│       ├── sample_handoff_12_section.md
│       ├── sample_ba_design.md
│       ├── sample_self_audit.md
│       └── sample_external_verdict.md
├── docs/
│   ├── superpowers/plans/                  # arcgentic's own round handoffs
│   ├── design/                             # arcgentic's BA design docs
│   ├── audits/                             # arcgentic's self-audit + external verdicts
│   ├── tech-debt.md
│   └── architecture/
│       └── adapter-layer.md
└── scripts/
    ├── fetch-references.sh
    ├── install-hooks.sh
    └── install-claude-code-skills.sh       # platform-specific installers
```

---

## § 19. Implementation order + dependencies

### 19.1 Dependency graph

```
                ┌─────────────────────┐
                │  adapter layer      │  (§ 3) — FOUNDATION
                │  (no deps)          │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │  audit_check.py     │  (§ 14.4) — used by hooks + skills
                │  (depends: adapter) │
                └──────────┬──────────┘
                           │
        ┌──────────────────┼─────────────────────┐
        │                  │                     │
   ┌────▼─────┐      ┌─────▼──────┐        ┌────▼──────┐
   │ planner  │      │ developer  │        │ cr/se/ba  │
   │ agent    │      │ agent      │        │ agents    │
   └────┬─────┘      └─────┬──────┘        └────┬──────┘
        │                  │                     │
        ▼                  ▼                     │
   ┌──────────┐      ┌──────────────────────────▼──────┐
   │plan-round│      │  execute-round (depends ALL above)│
   │ skill    │─────►│                                 │
   └──────────┘      └─────────────┬───────────────────┘
                                   │
                                   ▼
                       ┌───────────────────────┐
                       │ quality-gate-enforce  │
                       │ hook (depends on      │
                       │ audit_check)          │
                       └───────────────────────┘

  ─── P1 add-on (independent) ───

   ┌──────────────┐         ┌──────────────┐
   │codify-lesson │         │ track-refs   │
   │ skill        │         │ skill        │
   └──────┬───────┘         └──────┬───────┘
          │                        │
          ▼                        ▼
   ┌──────────────┐         ┌──────────────┐
   │lesson-       │         │ ref-tracker  │
   │ codifier     │         │ agent        │
   │ agent        │         │              │
   └──────────────┘         └──────────────┘
          │
          ▼
   ┌─────────────────────────┐
   │round-boundary-lesson-   │
   │ scan hook (depends:     │
   │ codify-lesson skill)    │
   └─────────────────────────┘

  ─── P2 ───
   ┌──────────────────────┐
   │cross-session-handoff │
   │ skill (independent)  │
   └──────────────────────┘
```

### 19.2 Implementation sequence

**Phase 1 (P0 — must-have for v0.2.0, ~18-21h)**:
1. Adapter layer (`arcgentic/adapters/*`) — ~4h
2. audit_check.py + tests — ~3h
3. ba-designer + cr-reviewer + se-contract agents (markdown briefs) — ~2h
4. developer + planner agents (markdown briefs) — ~2h
5. plan-round skill — ~3h
6. execute-round skill (the big one) — ~5h
7. pre-commit-fact-check hook + tests — ~1h
8. quality-gate-enforce hook + tests — ~1h
9. Templates (handoff 18/12/10-section, BA design, self-audit, external verdict) — ~2h
10. Integration test: end-to-end one round — ~2h

**Phase 2 (P1 add-on, ~9h)**:
11. codify-lesson skill + lesson-codifier agent — ~3h
12. track-refs skill + ref-tracker agent — ~3h
13. round-boundary-lesson-scan hook — ~1h
14. RT classifier module — ~1h
15. Pattern detection utility — ~1h

**Phase 3 (P2 nice-to-have, ~3h)**:
16. cross-session-handoff skill — ~2h
17. State lock mechanism — ~1h

### 19.3 Recommended split into sessions

- **Session 1 (Phase 1 P0; ~18h)**: ships v0.2.0 main release
- **Session 2 (Phase 2 P1; ~9h)**: ships v0.2.1 follow-on
- **Session 3 (Phase 3 P2; ~3h)**: ships v0.2.2 — typically can fold into Session 2 if time permits

---

## § 20. Acceptance criteria per skill

### 20.1 plan-round acceptance

- [ ] Given valid inputs, produces a handoff doc with exactly the section count for `template_size`
- [ ] All MUST sections present (per § 7.4 conditional matrix)
- [ ] Reference scan (§ 2) has ≥ 1 reference row with 4-column triplet
- [ ] § 12 audit fact-shape targets enumerates ≥ 25 facts
- [ ] No `TBD`, `TODO`, `XXX`, or `(fill in)` markers in MUST sections
- [ ] Writes file to `docs/superpowers/plans/{date}-{round_name}-handoff.md`
- [ ] Returns `handoff_path`, `section_count`, `loc`, `warnings`
- [ ] Round-name regex validation rejects malformed names
- [ ] Prior-round-anchor SHA-length validation (40-char required)

### 20.2 execute-round acceptance

- [ ] Given an existing handoff doc, produces 4 commits with correct subjects
- [ ] Commit 1 (entry-admin): updates handoff + CLAUDE.md + vault; no code
- [ ] Commit 2 (BA design): writes design doc; no code
- [ ] Commit 3 (dev body): writes source + tests; all 4 quality gates PASS before push
- [ ] Commit 4 (state refresh + audit handoff): writes audit handoff with N/N audit-check PASS
- [ ] Inline CR step produces § 2.2 table with ≥ 3 findings
- [ ] Inline SE step produces § 2.3 table with ≥ 3 NOVEL P3 findings
- [ ] SE brief does NOT contain BA design (mandate #20 isolation check)
- [ ] Quality gate failures escalate per § 4.2.4 retry table
- [ ] Push to origin/main after each commit
- [ ] `dry_run=True` skips all commits/pushes

### 20.3 codify-lesson acceptance

- [ ] Given last N round audit handoffs, detects pattern clusters
- [ ] Clusters with ≥ 3 occurrences → PROVISIONAL lesson
- [ ] Clusters with ≥ 5 occurrences → mandate amendment proposal
- [ ] Generates lesson card at `lessons/lesson-{N}-{slug}.md`
- [ ] Preservation streak updates correctly across rounds

### 20.4 track-refs acceptance

- [ ] Given a new reference repo, computes RT tier correctly per § 12 rules
- [ ] Appends repo block to `references/INDEX.md` in the correct format
- [ ] Detects CATEGORY tags from repo contents
- [ ] For BA design pass, emits 4-column triplet table snippet
- [ ] Round-relevance refresh updates all repo blocks

### 20.5 cross-session-handoff acceptance

- [ ] `read` returns current state without acquiring lock
- [ ] `write` acquires lock with TTL; releases after write
- [ ] Lock TTL expiry allows new sessions to acquire
- [ ] Atomic file operations (tmp + rename) prevent partial writes
- [ ] State history snapshots at round boundaries

### 20.6 Adapter layer acceptance

- [ ] `detect_adapter()` returns correct adapter for each IDE
- [ ] Claude Code adapter wraps Task/Skill/Read/Write/Edit/Bash correctly
- [ ] Cursor adapter falls back to inline mode gracefully
- [ ] VSCode-Codex adapter dispatches via Codex protocol
- [ ] Codex CLI adapter dispatches via CLI subprocess
- [ ] Inline adapter runs all agents in-process (no isolation; documented)

### 20.7 Hook acceptance

- [ ] `pre-commit-fact-check` excludes `*-external-audit-verdict.md` files
- [ ] `pre-commit-fact-check` fails commit if audit-check FAIL on any handoff
- [ ] `round-boundary-lesson-scan` runs after Phase 4 of execute-round
- [ ] `quality-gate-enforce` runs all 4 gates; returns exit 1 on any failure

### 20.8 audit-check acceptance

- [ ] Parses fact rows with all 5 recognized prefixes (`cd `, `git `, `uv run `, `bash `, `arcgentic `)
- [ ] Unescapes `\|` → `|` in command field
- [ ] Reports N pass / N fail / N skip
- [ ] `--strict` exits 1 on any FAIL or SKIP
- [ ] `--strict-extended` runs AC-1 Clauses A+B+C + AC-3
- [ ] AC-1 Clause A: verdict-claim vs fact count
- [ ] AC-1 Clause B: section refs resolve
- [ ] AC-1 Clause C: prose claims match expected
- [ ] AC-3: detection-capability check (no `≥` patterns)

---

## § 21. Test fixtures + sample data

### 21.1 Sample handoff doc (18-section)

The arcgentic dev session can use the Moirai R10-L3-social-multi-agent handoff as a reference structure (1056 LOC, 18 sections). The fixture file at `tests/fixtures/sample_handoff_18_section.md` should be a synthetic but realistic example following the § 7.1 template.

### 21.2 Sample BA design doc

Similarly, a synthetic BA design doc following § 8 template, with realistic D-1 to D-N decisions and reference scan triplet table.

### 21.3 Sample audit handoffs

Three samples covering substrate-touching / fix / admin round types.

### 21.4 Sample external audit verdicts

Two samples covering PASS / NEEDS_FIX outcomes.

### 21.5 Integration test scenario

```python
# tests/integration/test_end_to_end_round.py
"""End-to-end integration test for one complete round.

Tests the full 4-commit chain with mock adapters (no real git operations).
"""
import pytest
from pathlib import Path

from arcgentic.adapters.inline import InlineAdapter
from arcgentic.skills.plan_round import run as plan_round
from arcgentic.skills.execute_round import run as execute_round


def test_one_complete_round(tmp_path, monkeypatch):
    """plan-round → execute-round → 4 commits → audit-check PASS."""

    # Setup mock repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # ... initialize git, write CLAUDE.md, etc.

    # Phase 1: plan-round
    result = plan_round(
        round_name="R10-L3-test",
        round_type="substrate-touching",
        prior_round_anchor="a" * 40,
        scope_description="Test round for end-to-end integration",
    )
    assert result.handoff_path.exists()
    assert result.section_count == 18

    # Phase 2: execute-round
    execute_result = execute_round(
        round_name="R10-L3-test",
        handoff_path=result.handoff_path,
        dry_run=True,  # don't actually commit/push
    )
    assert execute_result.commits_planned == 4
    assert execute_result.cr_findings_count >= 3
    assert execute_result.se_findings_count >= 3
    assert execute_result.audit_check_pass is True
```

---

## § 22. Operational guidance for dev session

### 22.1 Recommended setup

1. **Clone arcgentic repo** to local workspace
2. **Install Python 3.13+** and `uv` (or pip + venv)
3. **Setup dev environment**:
   ```bash
   uv venv
   uv pip install -e ".[dev]"
   ```
4. **Verify quality gates work**:
   ```bash
   arcgentic audit-check tests/fixtures/sample_self_audit.md --strict-extended
   ```
5. **Install git hooks**:
   ```bash
   git config core.hooksPath .githooks
   ```

### 22.2 Working through Phase 1 (P0)

Follow § 19.2 sequence. Recommended approach:
- **Build foundation first**: adapters + audit-check + agent markdowns (Steps 1-4; ~11h)
- **Then skills**: plan-round + execute-round (Steps 5-6; ~8h) — execute-round depends on everything
- **Then hooks + templates**: enforce + templates (Steps 7-9; ~4h)
- **Then integration test**: end-to-end (Step 10; ~2h)

### 22.3 TDD discipline

For each skill/agent/hook:
1. Write failing tests first (per acceptance criteria in § 20)
2. Run `pytest` → confirm tests fail
3. Implement minimum code to pass tests
4. Run `pytest` → confirm tests pass
5. Run `mypy --strict` + `ruff` → fix any issues
6. Commit

### 22.4 Inline-self-finalization for arcgentic itself

arcgentic v0.2.0 should be developed using arcgentic v0.2.0's own workflow once Phase 1 ships. The first arcgentic round to use the new tooling is the round that completes Phase 2 (P1 add-on).

This eats-its-own-dogfood validation is essential. If arcgentic can't ship arcgentic's own v0.2.1 using v0.2.0 tooling, the tooling has a defect.

### 22.5 Common pitfalls

1. **Don't pass BA design to SE agent** (mandate #20). If you find yourself wanting to, the SE brief is incomplete; expand the threat surface enumeration instead.
2. **Don't skip `audit-check --strict-extended` on the self-audit handoff.** AC-1 + AC-3 catch drift that audit-check `--strict` alone misses.
3. **Don't write multi-line shell commands in fact-table commands.** Use single-line bash with `&&` chaining; multi-line breaks the parser.
4. **Don't use `≥ N` or `>= N` in fact expected values.** AC-3 will reject these.
5. **Don't commit `references/INDEX.md`.** It's gitignored (with the references themselves).
6. **Don't write directly to `state.yaml` without acquiring the lock.** Use `cross-session-handoff` skill API.

---

## § 23. Acknowledgments

This specification distills the discipline developed in Arc Studio's Moirai project across Phases 0-10. The 4-commit chain pattern, inline-self-finalization (mandate #17(d) clause (h) Option A), SE CONTRACT-ONLY isolation (mandate #20), RT tier vocabulary (mandate #13 (h)), and Lesson 8 STRUCTURAL-LAW protocol all originated in Moirai's engineering rigor mandates and have been observed across 12+ substrate-touching rounds with high preservation rates.

arcgentic adapts these patterns for general use across VSCode / Cursor / Codex / Claude Code, removing Moirai-specific naming conventions while preserving the structural discipline.

---

*End of arcgentic v0.2.0 — Complete Implementation Specification. ~5500 LOC; self-contained; ready for dev session ingestion.*
