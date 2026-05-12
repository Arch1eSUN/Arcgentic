# arcgentic v0.2.0 Spec Amendment 01 — Hybrid Monorepo Layout (Path C)

**Date**: 2026-05-13
**Author**: Founder (archiesun)
**Status**: AUTHORITATIVE — overrides spec § 18 + § 21.5 directory assumptions
**Trigger**: dev session surfaced cascade spec bug per CLAUDE.md § 6.2 plan-bug-fix policy
**Decided in**: chat exchange where dev session asked "目录布局" + founder responded "Path C — Hybrid Monorepo"

---

## 1. The cascade bug

Three constraints can't all be satisfied by a single layout:

1. **Plugin discovery** (Claude Code) expects `skills/<name>/SKILL.md` + `agents/<name>.md` at repo root.
2. **Python package imports** — spec § 21.5 fixture has `from arcgentic.adapters.inline import InlineAdapter` which requires `arcgentic/` to be a module-resolvable Python package.
3. **v0.1.0-alpha.2 already shipped** as CC plugin with constraint 1 satisfied + no Python package.

Spec § 18 attempted to satisfy 2 and ignored 1, putting markdown skills inside `arcgentic/skills/<name>.py` — which breaks CC discovery and contradicts the spec's own fixture import path conventions for plain SKILL.md files.

This is a **cascade spec bug** — the layout decision affects every file path, test path, plugin.json discovery contract, and CLI invocation.

---

## 2. The fix — Path C (Hybrid Monorepo, dual-surface)

ONE repo, TWO surfaces, each correctly addressing its constraint:

### 2.1 Plugin surface (repo root — preserves v0.1)

```
arcgentic/                              # repo root
├── plugin.json                         # CC plugin manifest (v0.1 contract, version bump only)
├── skills/                             # CC auto-discovery surface
│   ├── using-arcgentic/SKILL.md        # v0.1 (preserved)
│   ├── pre-round-scan/SKILL.md         # v0.1 (preserved)
│   ├── orchestrate-round/SKILL.md      # v0.1 (preserved)
│   ├── audit-round/SKILL.md            # v0.1 (preserved)
│   ├── verify-gates/SKILL.md           # v0.1 (preserved)
│   ├── plan-round/SKILL.md             # v0.2 NEW (P0)
│   ├── execute-round/SKILL.md          # v0.2 NEW (P0)
│   ├── codify-lesson/SKILL.md          # v0.2.1 (P1) — not in this session
│   ├── track-refs/SKILL.md             # v0.2.1 (P1) — not in this session
│   └── cross-session-handoff/SKILL.md  # v0.2.2 (P2) — not in this session
├── agents/                             # CC agent discovery
│   ├── orchestrator.md                 # v0.1 (preserved)
│   ├── auditor.md                      # v0.1 (preserved)
│   ├── planner.md                      # v0.2 NEW (P0)
│   ├── developer.md                    # v0.2 NEW (P0)
│   ├── ba-designer.md                  # v0.2 NEW (P0)
│   ├── cr-reviewer.md                  # v0.2 NEW (P0)
│   ├── se-contract.md                  # v0.2 NEW (P0)
│   ├── lesson-codifier.md              # v0.2.1 (P1) — not in this session
│   └── ref-tracker.md                  # v0.2.1 (P1) — not in this session
├── hooks/                              # CC hooks (Python)
│   ├── round-boundary-lesson-scan.py   # v0.2.1 (P1) — not in this session
│   └── quality-gate-enforce.py         # v0.2 NEW (P0)
├── .githooks/                          # Git hooks (Bash)
│   └── pre-commit                      # v0.2 NEW (P0) — invokes audit-check
├── scripts/                            # v0.1 Bash state machine + gates (preserved)
│   ├── state/
│   ├── gates/
│   ├── lib/
│   └── test-helpers.sh
├── schema/                             # v0.1 (preserved)
│   └── state.schema.json
└── tests/                              # v0.1 Bash test + dogfood (preserved)
    ├── integration/full-lifecycle.test.sh
    └── dogfood/...
```

### 2.2 Toolkit surface (`toolkit/` — NEW in v0.2)

```
toolkit/                                # publishable Python package
├── pyproject.toml                      # [project.scripts] arcgentic = "arcgentic.cli:main"
├── src/
│   └── arcgentic/                      # importable as `arcgentic`
│       ├── __init__.py
│       ├── cli.py                      # argparse entry-point
│       ├── audit_check.py              # § 14.4 fact-check engine + AC-1 + AC-3
│       ├── adapters/                   # § 3 IDE adapter layer
│       │   ├── __init__.py             # detect_adapter()
│       │   ├── base.py                 # IDEAdapter Protocol + AgentDispatchResult
│       │   ├── claude_code.py          # canonical reference impl
│       │   ├── cursor.py
│       │   ├── vscode_codex.py
│       │   ├── codex_cli.py
│       │   └── inline.py               # fallback — no subagent isolation
│       ├── skills_impl/                # algorithm implementations (called via CLI)
│       │   ├── __init__.py
│       │   ├── plan_round.py           # called by `arcgentic plan-round-impl`
│       │   └── execute_round.py        # called by `arcgentic execute-round-impl`
│       ├── mandates/
│       │   └── registry.yaml           # § 11 mandate ecosystem
│       └── utils/
│           ├── __init__.py
│           └── git_helpers.py
└── tests/                              # pytest suite
    ├── unit/
    │   ├── adapters/
    │   │   ├── test_base.py
    │   │   ├── test_detect.py
    │   │   ├── test_claude_code.py
    │   │   ├── test_cursor.py
    │   │   ├── test_vscode_codex.py
    │   │   ├── test_codex_cli.py
    │   │   └── test_inline.py
    │   ├── test_audit_check.py
    │   └── skills_impl/
    │       ├── test_plan_round.py
    │       └── test_execute_round.py
    └── integration/
        └── test_end_to_end_round.py    # § 21.5 fixture (revised import path)
```

### 2.3 Shared resources

```
arcgentic/
├── templates/                          # NEW — cross-surface markdown templates
│   ├── handoff_18_section.md           # § 7.1
│   ├── handoff_12_section.md           # § 7.2
│   ├── handoff_10_section.md           # § 7.3
│   ├── ba_design.md                    # § 8
│   ├── self_audit_handoff.md           # § 9
│   └── external_audit_verdict.md       # § 10
├── docs/                               # arcgentic's own dogfooding artifacts
│   ├── plans/
│   ├── audits/
│   └── examples/
├── README.md
├── README.zh-CN.md
└── LICENSE
```

---

## 3. Surface contract — how markdown skills invoke Python

Each new SKILL.md is a thin shim that shells out to the `arcgentic` CLI:

```markdown
# skills/plan-round/SKILL.md
---
name: plan-round
description: Generate a complete round handoff doc from scope + prior-round context. Use when starting a new round (substrate-touching / fix / admin).
---

# plan-round

Generates a round handoff at `docs/superpowers/plans/{date}-{round}-handoff.md`.

## Prerequisites

Requires the `arcgentic` CLI installed:
- Stable: `pipx install arcgentic` (post-v0.2.0 PyPI release)
- Dev: `pip install -e <repo>/toolkit/`

## When to invoke

- User says "let's plan R{N}" or invokes `/plan-round`
- New round-name without a handoff doc

## Workflow

When invoked with `$ARGUMENTS`:

1. Parse round_name + round_type + prior_anchor + scope_description from arguments
2. Validate inputs
3. Shell out: `arcgentic plan-round-impl --round=$ROUND --type=$TYPE --anchor=$ANCHOR`
4. The Python CLI does the heavy lifting (read prior context → dispatch planner agent via detect_adapter → validate output → write handoff)
5. Return the CLI's stdout to the user

## See also

- `toolkit/src/arcgentic/skills_impl/plan_round.py` — actual algorithm
- spec § 4.1 + § 5.1 (planner agent contract)
- `templates/handoff_18_section.md` (full-strength template)
```

---

## 4. Why Path C is the right call

1. **v0.1 plugin contract zero-break** — Claude Code users upgrading to v0.2 only need an extra `pipx install arcgentic` step. skills/agents paths unchanged; CC discovery mechanism unchanged.
2. **Algorithm centralization** — true logic lives in Python (verifiable via mypy / pytest / ruff). Markdown becomes pure trigger + brief documentation, NOT pseudo-code in prose.
3. **Cross-IDE feasibility** — `arcgentic` CLI is platform-neutral. Cursor / VSCode-Codex / Codex CLI users can shell out to it even though they lack CC-style skill auto-discovery.
4. **Testability + type safety** — spec § 21.5 fixture validates literally; `mypy --strict toolkit/src/` runs; CI can `pytest toolkit/tests/`.
5. **Distribution cleanliness** — plugin via CC marketplace; CLI via PyPI. Independent release cadences.

---

## 5. Spec § amendments (apply when reading spec)

| Spec § | Original assumption | Path C correction |
|---|---|---|
| § 18 | `arcgentic/skills/<name>.py` | Markdown skills at `skills/<name>/SKILL.md` (root). Python `skills_impl/<name>.py` at `toolkit/src/arcgentic/skills_impl/` |
| § 18 | `arcgentic/agents/<name>.md` | At repo root `agents/<name>.md` (CC convention) |
| § 18 | `arcgentic/templates/...` | At repo root `templates/...` (shared) |
| § 18 | `arcgentic/hooks/<name>.py` | At repo root `hooks/<name>.py` (CC convention) |
| § 18 | `tests/unit/...` at repo root | At `toolkit/tests/unit/...` (under Python package) |
| § 21.5 | `from arcgentic.adapters.inline import InlineAdapter` | VALID under Path C — runs from `toolkit/tests/integration/` |
| § 17.4 | `pyproject.toml` at repo root | At `toolkit/pyproject.toml` |

---

## 6. Migration record (v0.1.0-alpha.2 → v0.2.0-alpha.1)

**No changes to existing v0.1 files** — root-level `skills/<existing-5>/SKILL.md` + `agents/<existing-2>.md` + `scripts/` + `schema/` + `plugin.json` + `tests/` + `docs/` + `LICENSE` + `README*.md` stay intact.

**Add new (v0.2 P0 scope per CLAUDE.md § 4):**

| New directory | Contents | Estimated LOC |
|---|---|---|
| `toolkit/` | Python package + tests | ~2500-3000 |
| `templates/` | 6 markdown templates | ~500-800 |
| `skills/plan-round/` | SKILL.md (thin shim) | ~80 |
| `skills/execute-round/` | SKILL.md (thin shim) | ~100 |
| `agents/{planner,developer,ba-designer,cr-reviewer,se-contract}.md` | 5 agent briefs | ~150-250 each |
| `hooks/quality-gate-enforce.py` | Python hook | ~100-150 |
| `.githooks/pre-commit` | Bash hook | ~50-100 |

**Update (minimal):**

- v0.1 existing SKILL.md files: append "## Prerequisites" section noting `arcgentic` CLI dependency (only relevant for skills that will invoke CLI; verify-gates / audit-round may grow CLI invocation in P0)
- v0.1 existing agent.md files: NO changes (briefs already accept stateless prompt input)
- `plugin.json`: version bump to `0.2.0-alpha.1`; status string update
- `README.md` + `README.zh-CN.md`: status block update + P0/P1/P2 roadmap reflection

---

## 7. Scope note — what THIS session ships (v0.2.0 P0 only)

Per CLAUDE.md § 4, this session ships **only P0**:

| Deliverable | Status |
|---|---|
| 2 NEW skills: plan-round + execute-round | ✅ P0 (this session) |
| 5 NEW agents: planner + developer + ba-designer + cr-reviewer + se-contract | ✅ P0 (this session) |
| 2 NEW hooks: pre-commit-fact-check + quality-gate-enforce | ✅ P0 (this session) |
| audit_check.py + adapters layer + cli.py in toolkit/ | ✅ P0 (this session) |
| 3 handoff templates + BA design + self-audit + external verdict templates | ✅ P0 (this session) |
| codify-lesson skill + lesson-codifier agent + round-boundary-lesson-scan hook | ⏳ P1 (v0.2.1) |
| track-refs skill + ref-tracker agent | ⏳ P1 (v0.2.1) |
| cross-session-handoff skill | ⏳ P2 (v0.2.2) |

P1 skills/agents are listed in plugin.json (declarative-ahead) but NOT implemented this session.

---

## 8. Authority

This amendment is **AUTHORITATIVE** for the v0.2.0 P0 dev session. Where spec § 18 / § 21.5 / § 22 disagree with this amendment, this amendment wins. Future amendments (02, 03, ...) may further refine in `docs/plans/`.

— End of amendment 01 —
